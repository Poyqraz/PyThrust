"""Root and tip thrust split for V2 physics path."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_from_config,
    root_diameter_m,
    tip_radial_extension_from_config,
)
from ..models import FoldablePropellerConfig
from .aero import _coefficients_at_hover


@dataclass(frozen=True)
class SplitThrustResult:
    thrust_root_n: float
    thrust_tip_n: float
    thrust_total_n: float
    geometric_effective_diameter_m: float
    aerodynamic_effective_diameter_m: float
    tip_radial_extension_m: float


def _thrust_from_diameter(
    rpm: float,
    diameter_m: float,
    prop_entry: PropellerEntry,
    *,
    rho: float,
    scale: float = 1.0,
) -> float:
    if rpm <= 0.0 or diameter_m <= 0.0 or scale <= 0.0:
        return 0.0
    n = rpm / 60.0
    ct, _ = _coefficients_at_hover(rpm, prop_entry)
    return ct * rho * (n**2) * (diameter_m**4) * scale


def compute_split_thrust(
    *,
    rpm: float,
    theta_deg: float,
    tip_aero_effectiveness: float,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
    use_legacy_aggregate: bool = False,
) -> SplitThrustResult:
    """Compute root + tip thrust contributions."""
    geometry = config.geometry
    d_root = root_diameter_m(geometry)
    tip_ext = tip_radial_extension_from_config(theta_deg, config)
    d_geo = geometric_effective_diameter_from_config(theta_deg, config)
    d_aero = aerodynamic_effective_diameter_m(
        d_geo,
        root_diameter_m=d_root,
        tip_aero_effectiveness=tip_aero_effectiveness,
    )

    if use_legacy_aggregate:
        from .aero import quasi_steady_aero

        omega = rpm * math.pi / 30.0 if rpm > 0.0 else 0.0
        thrust, _, _ = quasi_steady_aero(
            omega,
            d_geo,
            prop_entry,
            rho=rho,
            aero_effectiveness=tip_aero_effectiveness,
        )
        return SplitThrustResult(
            thrust_root_n=thrust,
            thrust_tip_n=0.0,
            thrust_total_n=thrust,
            geometric_effective_diameter_m=d_geo,
            aerodynamic_effective_diameter_m=d_aero,
            tip_radial_extension_m=tip_ext,
        )

    thrust_root = _thrust_from_diameter(rpm, d_root, prop_entry, rho=rho, scale=1.0)

    d_tip_equiv = 2.0 * tip_ext if tip_ext > 0.0 else 0.0
    thrust_tip = _thrust_from_diameter(
        rpm,
        d_tip_equiv,
        prop_entry,
        rho=rho,
        scale=tip_aero_effectiveness,
    )

    return SplitThrustResult(
        thrust_root_n=thrust_root,
        thrust_tip_n=thrust_tip,
        thrust_total_n=thrust_root + thrust_tip,
        geometric_effective_diameter_m=d_geo,
        aerodynamic_effective_diameter_m=d_aero,
        tip_radial_extension_m=tip_ext,
    )
