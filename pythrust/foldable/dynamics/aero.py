"""Quasi-steady aerodynamic thrust and torque proxy (J=0 hover)."""

from __future__ import annotations

import math

from pythrust.propellers.database import PropellerEntry


def _coefficients_at_hover(
    rpm: float,
    prop_entry: PropellerEntry,
) -> tuple[float, float]:
    return prop_entry.get_coefficients(max(rpm, 0.0), 0.0)


def reference_propeller_thrust_n(
    rpm: float,
    diameter_m: float,
    prop_entry: PropellerEntry,
    *,
    rho: float = 1.225,
) -> float:
    """Open/reference propeller thrust at hover without foldable effectiveness loss."""
    if rpm <= 0.0 or diameter_m <= 0.0:
        return 0.0
    n = rpm / 60.0
    ct, _ = _coefficients_at_hover(rpm, prop_entry)
    return ct * rho * (n**2) * (diameter_m**4)


def quasi_steady_aero(
    omega_rad_s: float,
    effective_diameter_m: float,
    prop_entry: PropellerEntry,
    *,
    rho: float = 1.225,
    aero_effectiveness: float = 1.0,
) -> tuple[float, float, float]:
    """Return ``(thrust_n, aero_torque_nm, shaft_power_w)`` at hover (J=0).

    ``aero_effectiveness`` scales thrust and torque to approximate folded-blade
    overlap losses in dynamic V1 (1.0 = fully effective open geometry).
    """
    if omega_rad_s <= 0.0 or effective_diameter_m <= 0.0:
        return 0.0, 0.0, 0.0

    effectiveness = max(0.0, min(1.0, aero_effectiveness))
    rpm = omega_rad_s * 30.0 / math.pi
    n = omega_rad_s / (2.0 * math.pi)
    ct, cp = _coefficients_at_hover(rpm, prop_entry)

    d = effective_diameter_m
    thrust_n = ct * rho * (n**2) * (d**4) * effectiveness
    aero_torque_nm = cp * rho * (n**2) * (d**5) / (2.0 * math.pi) * effectiveness
    shaft_power_w = aero_torque_nm * omega_rad_s
    return thrust_n, aero_torque_nm, shaft_power_w
