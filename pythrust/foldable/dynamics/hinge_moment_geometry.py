"""Explicit geometric centrifugal opening-moment models for V2 hinge dynamics."""

from __future__ import annotations

import math
from typing import Literal

from ..kinematics import effective_hinge_radius_m, effective_tip_cg_from_hinge_m
from ..models import FoldablePropellerConfig

CentMomentModel = Literal["progress_lever", "geometric_radial"]

CENT_MOMENT_MODELS: tuple[CentMomentModel, ...] = ("progress_lever", "geometric_radial")


def effective_blade_angle_rad(theta_deg: float, config: FoldablePropellerConfig) -> float:
    """Blade angle in the rotation plane including deployment bias (rad).

    Convention: ``theta_deg = 0`` is fully open (radial outward),
    ``theta_deg = -180`` is parallel stow. ``deployment_bias_angle_deg`` shifts
    the angle used in the moment arm without moving hard stops — it models
    imperfect parallel fold (explicit assumption, default 0).
    """
    hinge = config.hinge
    return math.radians(theta_deg + hinge.deployment_bias_angle_deg)


def progress_lever_arm_m(theta_deg: float, config: FoldablePropellerConfig) -> float:
    """Legacy V2 lever: ``L * (1 - progress)`` — decreases linearly toward open."""
    hinge = config.hinge
    geometry = config.geometry
    span = hinge.theta_max_deg - hinge.theta_min_deg
    if abs(span) < 1e-12:
        return 0.0
    progress = (theta_deg - hinge.theta_min_deg) / span
    progress = max(0.0, min(1.0, progress))
    return geometry.tip_segment_length_m * (1.0 - progress)


def geometric_centrifugal_moment_arm_m(
    theta_deg: float,
    config: FoldablePropellerConfig,
) -> float:
    """Perpendicular moment arm for radial centrifugal force on tip CG (m).

    Derived from hinge at ``R_h`` and CG offset ``r_cg`` at blade angle ``phi``::

        M = m * omega^2 * R_h * r_cg * sin(-phi)

    The returned arm is ``R_h * r_cg * sin(-phi) / R_h`` scaled later — actually
    we return the effective lever ``R_h * sin(-phi)`` combined with r_cg in moment.
    """
    phi_rad = effective_blade_angle_rad(theta_deg, config)
    r_h = effective_hinge_radius_m(config.hinge, config.geometry)
    return r_h * math.sin(-phi_rad)


def centrifugal_moment_nm_for_model(
    rpm: float,
    theta_deg: float,
    config: FoldablePropellerConfig,
    *,
    model: CentMomentModel | None = None,
) -> float:
    """Centrifugal opening moment using the configured or overridden model."""
    if rpm <= 0.0:
        return 0.0

    selected: CentMomentModel = model or config.hinge.cent_moment_model
    omega = rpm * 2.0 * math.pi / 60.0
    geometry = config.geometry
    m = geometry.tip_segment_mass_kg
    r_cg = effective_tip_cg_from_hinge_m(geometry)
    scale = config.hinge.cent_moment_geometry_scale

    if selected == "progress_lever":
        lever = progress_lever_arm_m(theta_deg, config)
        if lever <= 0.0:
            return 0.0
        return scale * m * omega**2 * r_cg * lever

    if selected == "geometric_radial":
        r_h = effective_hinge_radius_m(config.hinge, config.geometry)
        phi_rad = effective_blade_angle_rad(theta_deg, config)
        sin_term = math.sin(-phi_rad)
        if abs(sin_term) < 1e-12:
            return 0.0
        return scale * m * omega**2 * r_h * r_cg * sin_term

    exhaustive: CentMomentModel = selected
    raise ValueError(f"Unknown cent_moment_model: {exhaustive!r}")


def initial_theta_deg(config: FoldablePropellerConfig) -> float:
    """Starting hinge angle including optional stow offset (explicit assumption)."""
    hinge = config.hinge
    theta = hinge.theta_min_deg + hinge.initial_stow_offset_deg
    return max(hinge.theta_min_deg, min(hinge.theta_max_deg, theta))
