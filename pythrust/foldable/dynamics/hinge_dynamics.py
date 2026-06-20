"""Second-order hinge dynamics integrator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ..models import FoldablePropellerConfig
from .hinge_moment_geometry import initial_theta_deg
from .hinge_moments import HingeMomentComponents, compute_hinge_moments, default_hinge_inertia_kgm2

HingeDynamicsMode = Literal["quasi_static", "second_order"]

MAX_THETA_DOT_RAD_S = 30.0


@dataclass
class HingeState:
    """Hinge angle state (radians internally for integration)."""

    theta_rad: float
    theta_dot_rad_s: float
    theta_ddot_rad_s2: float = 0.0

    @property
    def theta_deg(self) -> float:
        return math.degrees(self.theta_rad)

    @property
    def theta_dot_deg_s(self) -> float:
        return math.degrees(self.theta_dot_rad_s)

    @property
    def theta_ddot_deg_s2(self) -> float:
        return math.degrees(self.theta_ddot_rad_s2)


def _apply_open_latch_diagnostic(
    theta_rad: float,
    theta_dot_rad_s: float,
    config: FoldablePropellerConfig,
) -> tuple[float, float]:
    """Optional diagnostic latch: hold at open limit once capture threshold is reached."""
    hinge = config.hinge
    if not hinge.open_latch_diagnostic:
        return theta_rad, theta_dot_rad_s
    hi = math.radians(hinge.theta_max_deg)
    capture = math.radians(max(hinge.open_latch_capture_deg, 0.0))
    if theta_rad >= hi - capture:
        return hi, 0.0
    return theta_rad, theta_dot_rad_s


def _apply_limit_contact(
    theta_rad: float,
    theta_dot_rad_s: float,
    config: FoldablePropellerConfig,
) -> tuple[float, float]:
    """Inelastic contact at hard limits: zero velocity when on boundary."""
    lo = math.radians(config.hinge.theta_min_deg)
    hi = math.radians(config.hinge.theta_max_deg)
    if theta_rad <= lo + 1e-12:
        return lo, 0.0
    if theta_rad >= hi - 1e-12:
        return hi, 0.0
    clamped_dot = max(-MAX_THETA_DOT_RAD_S, min(MAX_THETA_DOT_RAD_S, theta_dot_rad_s))
    return theta_rad, clamped_dot


def _driving_moment_nm(moments: HingeMomentComponents) -> float:
    """Opening torque before Coulomb friction (stiffness resists opening)."""
    return (
        moments.M_centrifugal_nm
        + moments.M_aero_nm
        - moments.M_stiffness_nm
        - moments.M_damping_nm
        - moments.M_stop_nm
    )


def _breakaway_torque_nm(config: FoldablePropellerConfig) -> float:
    hinge = config.hinge
    coulomb = hinge.hinge_coulomb_friction_nm + hinge.hinge_friction_nm
    return hinge.hinge_breakaway_nm if hinge.hinge_breakaway_nm > 0.0 else coulomb


def _apply_stiction(
    theta_rad: float,
    theta_dot_rad_s: float,
    moments: HingeMomentComponents,
    config: FoldablePropellerConfig,
) -> tuple[float, float, float]:
    """Freeze hinge when driving torque cannot overcome breakaway friction."""
    M_drive = _driving_moment_nm(moments)
    if abs(M_drive) <= _breakaway_torque_nm(config):
        return theta_rad, 0.0, 0.0
    inertia = max(default_hinge_inertia_kgm2(config), 1e-18)
    return theta_rad, theta_dot_rad_s, moments.M_net_nm / inertia


def integrate_hinge_step(
    state: HingeState,
    *,
    dt_s: float,
    rpm: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
) -> HingeState:
    """RK2 step for J * theta_ddot = M_net with limit contact and stiction."""
    inertia = default_hinge_inertia_kgm2(config)
    if inertia <= 0.0:
        raise ValueError("hinge inertia must be positive for second_order dynamics.")

    latched_theta, latched_dot = _apply_open_latch_diagnostic(
        state.theta_rad, state.theta_dot_rad_s, config
    )
    hi = math.radians(config.hinge.theta_max_deg)
    if config.hinge.open_latch_diagnostic:
        if latched_theta != state.theta_rad or latched_dot != state.theta_dot_rad_s:
            return HingeState(
                theta_rad=latched_theta,
                theta_dot_rad_s=0.0,
                theta_ddot_rad_s2=0.0,
            )
        if abs(state.theta_rad - hi) < 1e-12:
            return HingeState(
                theta_rad=hi,
                theta_dot_rad_s=0.0,
                theta_ddot_rad_s2=0.0,
            )

    moments0 = compute_hinge_moments(
        rpm=rpm,
        theta_deg=state.theta_deg,
        theta_dot_rad_s=state.theta_dot_rad_s,
        tip_thrust_n=tip_thrust_n,
        config=config,
    )
    a1 = moments0.M_net_nm / inertia

    theta_dot_mid = state.theta_dot_rad_s + a1 * (dt_s / 2.0)
    theta_mid = state.theta_rad + theta_dot_mid * (dt_s / 2.0)
    moments_mid = compute_hinge_moments(
        rpm=rpm,
        theta_deg=math.degrees(theta_mid),
        theta_dot_rad_s=theta_dot_mid,
        tip_thrust_n=tip_thrust_n,
        config=config,
    )
    a2 = moments_mid.M_net_nm / inertia

    theta_dot_new = state.theta_dot_rad_s + a2 * dt_s
    theta_new = state.theta_rad + theta_dot_new * dt_s
    theta_new, theta_dot_new = _apply_limit_contact(theta_new, theta_dot_new, config)
    theta_new, theta_dot_new = _apply_open_latch_diagnostic(
        theta_new, theta_dot_new, config
    )

    moments_final = compute_hinge_moments(
        rpm=rpm,
        theta_deg=math.degrees(theta_new),
        theta_dot_rad_s=theta_dot_new,
        tip_thrust_n=tip_thrust_n,
        config=config,
    )
    theta_new, theta_dot_new, theta_ddot = _apply_stiction(
        theta_new, theta_dot_new, moments_final, config
    )

    return HingeState(
        theta_rad=theta_new,
        theta_dot_rad_s=theta_dot_new,
        theta_ddot_rad_s2=theta_ddot,
    )


def initial_hinge_state(config: FoldablePropellerConfig) -> HingeState:
    """Start at theta_min (+ optional initial_stow_offset_deg) with zero velocity."""
    return HingeState(
        theta_rad=math.radians(initial_theta_deg(config)),
        theta_dot_rad_s=0.0,
        theta_ddot_rad_s2=0.0,
    )


def hinge_moments_at_state(
    state: HingeState,
    *,
    rpm: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
) -> HingeMomentComponents:
    return compute_hinge_moments(
        rpm=rpm,
        theta_deg=state.theta_deg,
        theta_dot_rad_s=state.theta_dot_rad_s,
        tip_thrust_n=tip_thrust_n,
        config=config,
    )
