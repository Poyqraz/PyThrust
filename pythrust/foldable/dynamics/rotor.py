"""Rotor inertia and angular acceleration for dynamic spin-up."""

from __future__ import annotations

from ..models import FoldableGeometry, FoldablePropellerConfig

MOTOR_INERTIA_KGM2 = 1.0e-5


def default_rotor_inertia_kgm2(config: FoldablePropellerConfig) -> float:
    """Return configured or estimated rotor inertia (kg·m²)."""
    if config.geometry.rotor_inertia_kgm2 is not None:
        return config.geometry.rotor_inertia_kgm2
    geometry = config.geometry
    blade_inertia = _blade_pair_inertia_kgm2(geometry)
    return blade_inertia + MOTOR_INERTIA_KGM2


def _blade_pair_inertia_kgm2(geometry: FoldableGeometry) -> float:
    """Two-blade uniform-rod approximation about the hub."""
    span_m = geometry.hinge_position_m + geometry.tip_segment_length_m / 2.0
    mass_per_blade_kg = geometry.tip_segment_mass_kg * 5.0
    return (2.0 / 3.0) * mass_per_blade_kg * span_m**2


def rotor_acceleration_rad_s2(
    motor_torque_nm: float,
    aero_torque_nm: float,
    rotor_inertia_kgm2: float,
) -> float:
    """Rotor angular acceleration (rad/s²)."""
    if rotor_inertia_kgm2 <= 0.0:
        raise ValueError("rotor_inertia_kgm2 must be positive.")
    return (motor_torque_nm - aero_torque_nm) / rotor_inertia_kgm2
