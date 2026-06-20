"""Second-order hinge dynamics integrator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ..models import FoldablePropellerConfig
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


def _clamp_theta_and_velocity(
    theta_rad: float,
    theta_dot_rad_s: float,
    config: FoldablePropellerConfig,
) -> tuple[float, float]:
    lo = math.radians(config.hinge.theta_min_deg)
    hi = math.radians(config.hinge.theta_max_deg)
    if theta_rad <= lo + 1e-12:
        return lo, 0.0
    if theta_rad >= hi - 1e-12:
        return hi, 0.0
    clamped_dot = max(-MAX_THETA_DOT_RAD_S, min(MAX_THETA_DOT_RAD_S, theta_dot_rad_s))
    return theta_rad, clamped_dot


def _acceleration(
    theta_rad: float,
    theta_dot_rad_s: float,
    *,
    rpm: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
    inertia: float,
) -> tuple[float, HingeMomentComponents]:
    moments = compute_hinge_moments(
        rpm=rpm,
        theta_deg=math.degrees(theta_rad),
        theta_dot_rad_s=theta_dot_rad_s,
        tip_thrust_n=tip_thrust_n,
        config=config,
    )
    return moments.M_net_nm / inertia, moments


def integrate_hinge_step(
    state: HingeState,
    *,
    dt_s: float,
    rpm: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
) -> HingeState:
    """RK2 step for J * theta_ddot = M_net with hard-stop clamping."""
    inertia = default_hinge_inertia_kgm2(config)
    if inertia <= 0.0:
        raise ValueError("hinge inertia must be positive for second_order dynamics.")

    a1, _ = _acceleration(
        state.theta_rad,
        state.theta_dot_rad_s,
        rpm=rpm,
        tip_thrust_n=tip_thrust_n,
        config=config,
        inertia=inertia,
    )
    theta_dot_mid = state.theta_dot_rad_s + a1 * (dt_s / 2.0)
    theta_mid = state.theta_rad + theta_dot_mid * (dt_s / 2.0)
    a2, moments = _acceleration(
        theta_mid,
        theta_dot_mid,
        rpm=rpm,
        tip_thrust_n=tip_thrust_n,
        config=config,
        inertia=inertia,
    )

    theta_dot_new = state.theta_dot_rad_s + a2 * dt_s
    theta_new = state.theta_rad + theta_dot_new * dt_s
    theta_new, theta_dot_new = _clamp_theta_and_velocity(theta_new, theta_dot_new, config)

    return HingeState(
        theta_rad=theta_new,
        theta_dot_rad_s=theta_dot_new,
        theta_ddot_rad_s2=a2,
    )


def initial_hinge_state(config: FoldablePropellerConfig) -> HingeState:
    """Start folded at theta_min with zero velocity."""
    return HingeState(
        theta_rad=math.radians(config.hinge.theta_min_deg),
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
