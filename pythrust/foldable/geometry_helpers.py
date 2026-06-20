"""V2 foldable geometry helpers: parallel-stow radial extension and effective diameters."""

from __future__ import annotations

import math
from typing import Literal

from .models import FoldableGeometry, FoldablePropellerConfig

StowModel = Literal["legacy_cos", "parallel_fold"]


def tip_radial_extension_m(
    theta_deg: float,
    geometry: FoldableGeometry,
    *,
    stow_model: StowModel = "parallel_fold",
) -> float:
    """Radial tip contribution beyond the hinge (m).

    ``parallel_fold`` (V2):
        extension = L * max(0, (cos(theta) + 1) / 2)
        - theta = -180 deg (parallel stow): 0
        - theta = 0 deg (open): L

    ``legacy_cos`` (V1):
        extension = L * cos(theta)  (can be negative; clamped to 0)
    """
    length_m = geometry.tip_segment_length_m
    theta_rad = math.radians(theta_deg)
    if stow_model == "legacy_cos":
        return max(0.0, length_m * math.cos(theta_rad))
    return length_m * max(0.0, (math.cos(theta_rad) + 1.0) / 2.0)


def geometric_effective_diameter_m(
    theta_deg: float,
    geometry: FoldableGeometry,
    *,
    stow_model: StowModel = "parallel_fold",
) -> float:
    """Geometric effective diameter from hinge position + radial tip extension."""
    extension = tip_radial_extension_m(theta_deg, geometry, stow_model=stow_model)
    return 2.0 * (geometry.hinge_position_m + extension)


def aerodynamic_effective_diameter_m(
    geometric_diameter_m: float,
    *,
    root_diameter_m: float,
    tip_aero_effectiveness: float,
) -> float:
    """Linear blend: root always active; tip annulus scaled by lagged effectiveness."""
    eff = max(0.0, min(1.0, tip_aero_effectiveness))
    return root_diameter_m + eff * (geometric_diameter_m - root_diameter_m)


def root_diameter_m(geometry: FoldableGeometry) -> float:
    """Diameter from hub to hinge (root segment only)."""
    return 2.0 * geometry.hinge_position_m


def resolve_stow_model(config: FoldablePropellerConfig) -> StowModel:
    """Return stow model from config geometry."""
    model = config.geometry.stow_model
    if model == "parallel_fold":
        return "parallel_fold"
    return "legacy_cos"


def geometric_effective_diameter_from_config(
    theta_deg: float,
    config: FoldablePropellerConfig,
) -> float:
    """Geometric D_eff using config stow model."""
    stow = resolve_stow_model(config)
    return geometric_effective_diameter_m(theta_deg, config.geometry, stow_model=stow)


def tip_radial_extension_from_config(
    theta_deg: float,
    config: FoldablePropellerConfig,
) -> float:
    """Tip radial extension using config stow model."""
    stow = resolve_stow_model(config)
    return tip_radial_extension_m(theta_deg, config.geometry, stow_model=stow)
