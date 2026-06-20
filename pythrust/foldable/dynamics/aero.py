"""Quasi-steady aerodynamic thrust and torque proxy (J=0 hover)."""

from __future__ import annotations

import math

from pythrust.propellers.database import PropellerEntry


def quasi_steady_aero(
    omega_rad_s: float,
    effective_diameter_m: float,
    prop_entry: PropellerEntry,
    *,
    rho: float = 1.225,
) -> tuple[float, float, float]:
    """Return ``(thrust_n, aero_torque_nm, shaft_power_w)`` at hover (J=0)."""
    if omega_rad_s <= 0.0 or effective_diameter_m <= 0.0:
        return 0.0, 0.0, 0.0

    rpm = omega_rad_s * 30.0 / math.pi
    n = omega_rad_s / (2.0 * math.pi)
    ct, cp = prop_entry.get_coefficients(rpm, 0.0)

    d = effective_diameter_m
    thrust_n = ct * rho * (n**2) * (d**4)
    aero_torque_nm = cp * rho * (n**2) * (d**5) / (2.0 * math.pi)
    shaft_power_w = aero_torque_nm * omega_rad_s
    return thrust_n, aero_torque_nm, shaft_power_w
