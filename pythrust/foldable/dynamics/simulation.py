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
from .aero_effectiveness import (
    FOLDED_MIN_AERO_EFFECTIVENESS,
    aero_effectiveness_from_progress,
    deployment_progress_from_theta,
)
from .hinge import quasi_static_theta_deg
from .integrator import euler_step
from .motor import algebraic_motor_current, applied_voltage_v, motor_torque_nm
from .rotor import default_rotor_inertia_kgm2, rotor_acceleration_rad_s2
from .state import SPINUP_CSV_COLUMNS, DynamicState
from .throttle import ThrottleProfileName, throttle_at_time

MODEL_ASSUMPTIONS: tuple[str, ...] = (
    "Algebraic motor current (no electrical inductance).",
    "Fixed rotor inertia from blade geometry estimate plus motor offset.",
    "Quasi-static hinge: theta follows moment equilibrium at current RPM "
    "(not a second-order hinge ODE).",
    "Quasi-steady aero at J=0; Ct/Cp from reference propeller database with D_eff.",
    "Dynamic V1 aero_effectiveness scales thrust/torque by deployment progress "
    f"(folded floor={FOLDED_MIN_AERO_EFFECTIVENESS:.2f}); V1 approximation only, "
    "not a full folded-blade aero model.",
    "D_eff is aerodynamic effective diameter during deployment, not the 0.14 m "
    "stowed_envelope_diameter_m storage target.",
    "Thrust and aero torque zero at omega=0.",
    "Throttle step profile is an ideal command (instant full throttle after t=0).",
    "Throttle linear_ramp profile is more realistic for startup visualization "
    "(default ramp_time_s=0.5 s).",
    "ideal_geometry_ratio_at_7100_rpm is not experimental performance; it assumes "
    "no profile/hinge/manufacturing loss once fully deployed.",
    "0.70 pretest and 0.85 project ratios are calibration/target references "
    "against the same-diameter standard propeller; not automatically achieved by V1.",
    "Static foldable model unchanged; additive dynamics layer only.",
)


@dataclass(frozen=True)
class SpinUpConfig:
    """Time-stepping and throttle parameters for V1 skeleton."""

    dt_s: float = 0.01
    t_end_s: float = 3.0
    rho_kg_m3: float = 1.225
    throttle_profile: ThrottleProfileName = "step"
    ramp_time_s: float = 0.5


def build_throttle_schedule(
    spinup: SpinUpConfig,
) -> Callable[[float], float]:
    """Build a throttle schedule callable from spin-up config."""

    def schedule(time_s: float) -> float:
        return throttle_at_time(
            time_s,
            profile=spinup.throttle_profile,
            ramp_time_s=spinup.ramp_time_s,
        )

    return schedule


def default_throttle_schedule(time_s: float) -> float:
    """Backward-compatible step schedule: 0 at t=0, 1.0 after."""
    return throttle_at_time(time_s, profile="step")


def run_spinup_simulation(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    spinup: SpinUpConfig | None = None,
    throttle_schedule: Callable[[float], float] | None = None,
) -> List[DynamicState]:
    """Integrate rotor spin-up with quasi-static hinge and quasi-steady aero."""
    params = spinup or SpinUpConfig()
    schedule = throttle_schedule or build_throttle_schedule(params)
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

        deployment_progress = deployment_progress_from_theta(
            theta_deg,
            theta_min_deg=config.hinge.theta_min_deg,
            theta_max_deg=config.hinge.theta_max_deg,
        )
        aero_eff = aero_effectiveness_from_progress(deployment_progress)

        current_a = algebraic_motor_current(omega_rad_s, throttle, config)
        q_motor = motor_torque_nm(omega_rad_s, throttle, config)
        d_eff = effective_diameter_m(theta_deg, config)
        thrust_n, q_aero, power_w = quasi_steady_aero(
            omega_rad_s,
            d_eff,
            prop_entry,
            rho=params.rho_kg_m3,
            aero_effectiveness=aero_eff,
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
                deployment_progress_01=round(deployment_progress, 6),
                aero_effectiveness=round(aero_eff, 6),
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
