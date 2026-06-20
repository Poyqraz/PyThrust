"""Lagged tip aerodynamic effectiveness for V2 physics path."""

from __future__ import annotations

from ..geometry_helpers import tip_radial_extension_from_config
from ..models import FoldablePropellerConfig


def geometric_tip_exposure_01(theta_deg: float, config: FoldablePropellerConfig) -> float:
    """Normalized tip radial exposure in [0, 1]."""
    length = config.geometry.tip_segment_length_m
    if length <= 0.0:
        return 0.0
    extension = tip_radial_extension_from_config(theta_deg, config)
    return max(0.0, min(1.0, extension / length))


def update_tip_aero_effectiveness(
    current_eff: float,
    theta_deg: float,
    *,
    dt_s: float,
    config: FoldablePropellerConfig,
) -> float:
    """First-order lag: tau * d(eff)/dt = f_geom(theta) - eff."""
    target = geometric_tip_exposure_01(theta_deg, config)
    tau = config.hinge.tip_aero_lag_tau_s
    if tau <= 0.0 or dt_s <= 0.0:
        return target
    alpha = min(1.0, dt_s / tau)
    return current_eff + alpha * (target - current_eff)
