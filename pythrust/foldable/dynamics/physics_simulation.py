"""Propeller-first prescribed-RPM physics simulation (no motor module)."""

from __future__ import annotations

from typing import List

from pythrust.propellers.database import PropellerEntry

from ..kinematics import classify_physics_hinge_state
from ..models import FoldablePropellerConfig
from .hinge_dynamics import HingeState, initial_hinge_state, integrate_hinge_step, hinge_moments_at_state
from .physics_state import PhysicsState
from .prescribed_rpm import PrescribedRpmConfig
from .split_thrust import compute_split_thrust
from .tip_aero_effectiveness import update_tip_aero_effectiveness


def run_prescribed_rpm_physics(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    sim: PrescribedRpmConfig | None = None,
) -> list[PhysicsState]:
    """Run foldable blade physics with prescribed RPM (propeller-first path)."""
    sim_config = sim or PrescribedRpmConfig()
    rpm_schedule = sim_config.build_schedule()
    dt_s = sim_config.dt_s
    t_end_s = sim_config.t_end_s

    hinge = initial_hinge_state(config)
    tip_aero_eff = 0.0
    states: List[PhysicsState] = []
    time_s = 0.0
    step_count = max(1, int(round(t_end_s / dt_s)))

    for step in range(step_count + 1):
        rpm = rpm_schedule(time_s)
        split = compute_split_thrust(
            rpm=rpm,
            theta_deg=hinge.theta_deg,
            tip_aero_effectiveness=tip_aero_eff,
            config=config,
            prop_entry=prop_entry,
            rho=sim_config.rho_kg_m3,
        )
        moments = hinge_moments_at_state(
            hinge,
            rpm=rpm,
            tip_thrust_n=split.thrust_tip_n,
            config=config,
        )
        opening = moments.M_centrifugal_nm + moments.M_aero_nm
        resisting = (
            moments.M_stiffness_nm
            + moments.M_damping_nm
            + moments.M_friction_nm
            + moments.M_stop_nm
        )
        hinge_state = classify_physics_hinge_state(
            rpm,
            hinge.theta_deg,
            hinge.theta_dot_deg_s,
            opening,
            resisting,
            config.hinge,
        )

        states.append(
            PhysicsState(
                time_s=time_s,
                rpm=rpm,
                theta_deg=hinge.theta_deg,
                theta_dot_deg_s=hinge.theta_dot_deg_s,
                theta_ddot_deg_s2=hinge.theta_ddot_deg_s2,
                tip_radial_extension_m=split.tip_radial_extension_m,
                geometric_effective_diameter_m=split.geometric_effective_diameter_m,
                aerodynamic_effective_diameter_m=split.aerodynamic_effective_diameter_m,
                M_centrifugal_nm=moments.M_centrifugal_nm,
                M_aero_nm=moments.M_aero_nm,
                M_stiffness_nm=moments.M_stiffness_nm,
                M_damping_nm=moments.M_damping_nm,
                M_friction_nm=moments.M_friction_nm,
                M_stop_nm=moments.M_stop_nm,
                M_net_nm=moments.M_net_nm,
                thrust_root_n=split.thrust_root_n,
                thrust_tip_n=split.thrust_tip_n,
                thrust_total_n=split.thrust_total_n,
                hinge_state=hinge_state,
            )
        )

        if step >= step_count:
            break

        hinge = integrate_hinge_step(
            hinge,
            dt_s=dt_s,
            rpm=rpm,
            tip_thrust_n=split.thrust_tip_n,
            config=config,
        )
        tip_aero_eff = update_tip_aero_effectiveness(
            tip_aero_eff,
            hinge.theta_deg,
            dt_s=dt_s,
            config=config,
        )
        time_s += dt_s

    return states
