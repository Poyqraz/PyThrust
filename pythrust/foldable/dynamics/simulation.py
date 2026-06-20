"""Dynamic spin-up simulation orchestrator and CSV export."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Sequence

from pythrust.propellers.database import PropellerEntry

from ..effective_diameter import effective_diameter_m
from ..kinematics import (
    classify_hinge_state,
    opening_moment_nm,
    resisting_moment_nm,
)
from ..models import FoldablePropellerConfig
from .aero import quasi_steady_aero
from .hinge import quasi_static_theta_deg
from .integrator import euler_step
from .motor import algebraic_motor_current, applied_voltage_v, motor_torque_nm
from .rotor import default_rotor_inertia_kgm2, rotor_acceleration_rad_s2
from .state import SPINUP_CSV_COLUMNS, DynamicState

MODEL_ASSUMPTIONS: tuple[str, ...] = (
    "Algebraic motor current (no electrical inductance).",
    "Fixed rotor inertia from blade geometry estimate plus motor offset.",
    "Quasi-static hinge: theta follows moment equilibrium at current RPM.",
    "Quasi-steady aero at J=0; Ct/Cp from reference propeller database with D_eff.",
    "Thrust and aero torque zero at omega=0.",
    "Step throttle input; no ESC ramp model.",
    "Static foldable model unchanged; additive dynamics layer only.",
)


@dataclass(frozen=True)
class SpinUpConfig:
    """Time-stepping parameters for V1 skeleton."""

    dt_s: float = 0.01
    t_end_s: float = 3.0
    rho_kg_m3: float = 1.225


def default_throttle_schedule(time_s: float) -> float:
    """Motor off at t=0; full throttle immediately after."""
    return 1.0 if time_s > 0.0 else 0.0


def run_spinup_simulation(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    spinup: SpinUpConfig | None = None,
    throttle_schedule: Callable[[float], float] | None = None,
) -> List[DynamicState]:
    """Integrate rotor spin-up with quasi-static hinge and quasi-steady aero."""
    params = spinup or SpinUpConfig()
    schedule = throttle_schedule or default_throttle_schedule
    rotor_inertia = default_rotor_inertia_kgm2(config)

    n_steps = int(round(params.t_end_s / params.dt_s))
    omega_rad_s = 0.0
    psi_rad = 0.0
    theta_deg = config.hinge.theta_min_deg
    theta_deg_prev = theta_deg

    states: List[DynamicState] = []

    for step_index in range(n_steps + 1):
        time_s = step_index * params.dt_s
        throttle = schedule(time_s)
        rpm = max(0.0, omega_rad_s * 30.0 / math.pi)
        theta_dot_deg_s = 0.0 if step_index == 0 else (theta_deg - theta_deg_prev) / params.dt_s

        current_a = algebraic_motor_current(omega_rad_s, throttle, config)
        q_motor = motor_torque_nm(omega_rad_s, throttle, config)
        d_eff = effective_diameter_m(theta_deg, config)
        thrust_n, q_aero, power_w = quasi_steady_aero(
            omega_rad_s,
            d_eff,
            prop_entry,
            rho=params.rho_kg_m3,
        )
        m_open = opening_moment_nm(rpm, config.geometry, config.hinge)
        m_resist = resisting_moment_nm(theta_deg, config.hinge)
        hinge_state = classify_hinge_state(
            rpm,
            theta_deg,
            m_open,
            m_resist,
            config.hinge,
        )

        states.append(
            DynamicState(
                time_s=round(time_s, 6),
                throttle=round(throttle, 4),
                voltage_v=round(applied_voltage_v(throttle, config), 4),
                current_a=round(current_a, 6),
                omega_rad_s=round(omega_rad_s, 6),
                rpm=round(rpm, 4),
                rotor_azimuth_deg=round(math.degrees(psi_rad), 4),
                theta_deg=round(theta_deg, 4),
                theta_dot_deg_s=round(theta_dot_deg_s, 4),
                effective_diameter_m=round(d_eff, 6),
                opening_moment_nm=round(m_open, 6),
                resisting_moment_nm=round(m_resist, 6),
                motor_torque_nm=round(q_motor, 6),
                aero_torque_nm=round(q_aero, 6),
                thrust_n=round(thrust_n, 6),
                power_w=round(power_w, 4),
                hinge_state=hinge_state,
            )
        )

        if step_index == n_steps:
            break

        d_omega = rotor_acceleration_rad_s2(q_motor, q_aero, rotor_inertia)
        omega_rad_s = euler_step(omega_rad_s, d_omega, params.dt_s)
        omega_rad_s = max(0.0, omega_rad_s)
        psi_rad = euler_step(psi_rad, omega_rad_s, params.dt_s)

        theta_deg_prev = theta_deg
        rpm_new = omega_rad_s * 30.0 / math.pi
        theta_deg = quasi_static_theta_deg(rpm_new, config)

    return states


def write_spinup_csv(
    path: str | Path,
    states: Sequence[DynamicState],
) -> Path:
    """Write simulation history to CSV with the fixed column schema."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SPINUP_CSV_COLUMNS))
        writer.writeheader()
        for state in states:
            writer.writerow(state.to_csv_row())
    return output_path
