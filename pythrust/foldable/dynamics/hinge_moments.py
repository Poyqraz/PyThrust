"""Hinge moment component model for V2 second-order dynamics."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..models import FoldablePropellerConfig
from ..geometry_helpers import tip_radial_extension_from_config
from .hinge_moment_geometry import centrifugal_moment_nm_for_model


@dataclass(frozen=True)
class HingeMomentComponents:
    """Separate hinge moment contributions (N·m)."""

    M_centrifugal_nm: float
    M_aero_nm: float
    M_stiffness_nm: float
    M_damping_nm: float
    M_friction_nm: float
    M_stop_nm: float
    M_net_nm: float


def centrifugal_moment_nm(
    rpm: float,
    theta_deg: float,
    config: FoldablePropellerConfig,
) -> float:
    return centrifugal_moment_nm_for_model(rpm, theta_deg, config)


def stiffness_moment_nm(theta_deg: float, config: FoldablePropellerConfig) -> float:
    hinge = config.hinge
    theta_rad = math.radians(theta_deg)
    theta_min_rad = math.radians(hinge.theta_min_deg)
    return hinge.hinge_stiffness_nm_per_rad * (theta_rad - theta_min_rad)


def damping_moment_nm(theta_dot_rad_s: float, config: FoldablePropellerConfig) -> float:
    return config.hinge.hinge_damping_nm_s_per_rad * theta_dot_rad_s


FRICTION_VEL_REG_RAD_S = 0.25


def coulomb_friction_moment_nm(
    theta_dot_rad_s: float,
    M_net_without_friction_nm: float,
    config: FoldablePropellerConfig,
) -> float:
    """Coulomb friction with tanh regularization; full stick when below breakaway."""
    hinge = config.hinge
    coulomb = hinge.hinge_coulomb_friction_nm + hinge.hinge_friction_nm
    breakaway = hinge.hinge_breakaway_nm if hinge.hinge_breakaway_nm > 0.0 else coulomb
    if abs(M_net_without_friction_nm) <= breakaway:
        return M_net_without_friction_nm
    if abs(theta_dot_rad_s) < 1e-9:
        return breakaway if M_net_without_friction_nm > 0.0 else -breakaway
    return coulomb * math.tanh(theta_dot_rad_s / FRICTION_VEL_REG_RAD_S)


def stop_moment_nm(theta_deg: float, config: FoldablePropellerConfig) -> float:
    """Penalty only when theta exceeds hard limits (not at rest on folded stop)."""
    hinge = config.hinge
    k_stop = hinge.stop_stiffness_nm_per_rad
    if k_stop <= 0.0:
        return 0.0
    moment = 0.0
    lower = hinge.theta_min_deg
    upper = hinge.theta_max_deg
    if theta_deg < lower:
        moment += k_stop * math.radians(lower - theta_deg)
    if theta_deg > upper:
        moment -= k_stop * math.radians(theta_deg - upper)
    return moment


def aero_hinge_moment_nm(
    rpm: float,
    theta_deg: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
) -> float:
    """Proxy hinge moment from tip normal force × lever arm."""
    gain = config.hinge.aero_hinge_moment_gain
    if gain <= 0.0 or rpm <= 0.0:
        return 0.0
    extension = tip_radial_extension_from_config(theta_deg, config)
    if extension <= 0.0:
        return 0.0
    lever = config.geometry.tip_segment_length_m * (extension / config.geometry.tip_segment_length_m)
    return gain * tip_thrust_n * lever


def compute_hinge_moments(
    *,
    rpm: float,
    theta_deg: float,
    theta_dot_rad_s: float,
    tip_thrust_n: float,
    config: FoldablePropellerConfig,
) -> HingeMomentComponents:
    """Compute all hinge moment components and net opening moment."""
    M_cent = centrifugal_moment_nm(rpm, theta_deg, config)
    M_stiff = stiffness_moment_nm(theta_deg, config)
    M_damp = damping_moment_nm(theta_dot_rad_s, config)
    M_stop = stop_moment_nm(theta_deg, config)
    M_aero = aero_hinge_moment_nm(rpm, theta_deg, tip_thrust_n, config)

    M_without_fric = M_cent + M_aero - M_stiff - M_damp - M_stop
    M_fric = coulomb_friction_moment_nm(theta_dot_rad_s, M_without_fric, config)
    M_net = M_without_fric - M_fric

    return HingeMomentComponents(
        M_centrifugal_nm=M_cent,
        M_aero_nm=M_aero,
        M_stiffness_nm=M_stiff,
        M_damping_nm=M_damp,
        M_friction_nm=M_fric,
        M_stop_nm=M_stop,
        M_net_nm=M_net,
    )


def default_hinge_inertia_kgm2(config: FoldablePropellerConfig) -> float:
    """Estimate hinge inertia from tip segment (rod about hinge)."""
    if config.hinge.hinge_inertia_kgm2 is not None:
        return config.hinge.hinge_inertia_kgm2
    m = config.geometry.tip_segment_mass_kg
    L = config.geometry.tip_segment_length_m
    return m * L**2 / 3.0
