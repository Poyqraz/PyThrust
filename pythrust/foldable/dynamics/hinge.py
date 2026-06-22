"""Quasi-static hinge update using the existing moment-based kinematics model."""

from __future__ import annotations

from ..kinematics import theta_deg_moment_based
from ..models import FoldablePropellerConfig
from .hinge_dynamics import HingeState, initial_hinge_state, integrate_hinge_step

__all__ = [
    "HingeState",
    "initial_hinge_state",
    "integrate_hinge_step",
    "quasi_static_theta_deg",
]


def quasi_static_theta_deg(rpm: float, config: FoldablePropellerConfig) -> float:
    """Hinge angle from moment equilibrium at the current RPM (degrees)."""
    if rpm <= 0.0:
        return config.hinge.theta_min_deg
    return theta_deg_moment_based(rpm, config)
