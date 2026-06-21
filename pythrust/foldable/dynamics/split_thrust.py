"""Root and tip thrust split for V2 physics path."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_from_config,
    root_diameter_m,
    tip_radial_extension_from_config,
)
from ..models import FoldablePropellerConfig
from .aero import _coefficients_at_hover

ThrustSplitMode = Literal[
    "independent_tip_disk",
    "effective_diameter_delta",
    "annular_extension_proxy",
    "calibrated_effective_diameter_delta",
]

THRUST_SPLIT_MODES: tuple[ThrustSplitMode, ...] = (
    "independent_tip_disk",
    "effective_diameter_delta",
    "annular_extension_proxy",
    "calibrated_effective_diameter_delta",
)

MODE_NOTES: dict[ThrustSplitMode, str] = {
    "independent_tip_disk": "Legacy: tip as standalone disk d_tip=2*extension, T_tip~d_tip^4",
    "effective_diameter_delta": "BEM-lite: T_tip=max(T(D_aero)-T(D_root),0)",
    "annular_extension_proxy": "BEM-lite: annulus area fraction of full-open increment",
    "calibrated_effective_diameter_delta": (
        "Calibrated BEM-lite delta: ideal tip delta × fixed tip_delta_efficiency_factor "
        "(pretest 70% or target 85% of 25 cm reference, from latch_theta0)"
    ),
}


@dataclass(frozen=True)
class SplitThrustResult:
    thrust_root_n: float
    thrust_tip_n: float
    thrust_total_n: float
    geometric_effective_diameter_m: float
    aerodynamic_effective_diameter_m: float
    tip_radial_extension_m: float


def _thrust_scale(config: FoldablePropellerConfig) -> float:
    return max(config.calibration.k_thrust, 0.0)


def _resolve_split_mode(
    config: FoldablePropellerConfig,
    split_mode: ThrustSplitMode | None,
) -> ThrustSplitMode:
    selected = split_mode or config.calibration.thrust_split_mode
    if selected not in THRUST_SPLIT_MODES:
        raise ValueError(f"Unknown thrust_split_mode: {selected!r}")
    return selected


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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _split_independent_tip_disk(
    *,
    rpm: float,
    d_root: float,
    tip_ext: float,
    tip_aero_effectiveness: float,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
) -> tuple[float, float, float]:
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=thrust_scale
    )
    d_tip_equiv = 2.0 * tip_ext if tip_ext > 0.0 else 0.0
    thrust_tip = _thrust_from_diameter(
        rpm,
        d_tip_equiv,
        prop_entry,
        rho=rho,
        scale=thrust_scale * _clamp01(tip_aero_effectiveness),
    )
    return thrust_root, thrust_tip, thrust_root + thrust_tip


def _split_effective_diameter_delta(
    *,
    rpm: float,
    d_root: float,
    d_aero: float,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
) -> tuple[float, float, float]:
    """Effective diameter delta proxy (BEM-lite, not full BEM)."""
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=thrust_scale
    )
    thrust_total_aero = _thrust_from_diameter(
        rpm, d_aero, prop_entry, rho=rho, scale=thrust_scale
    )
    thrust_tip = max(thrust_total_aero - thrust_root, 0.0)
    return thrust_root, thrust_tip, thrust_root + thrust_tip


def _split_annular_extension_proxy(
    *,
    rpm: float,
    d_root: float,
    d_geo: float,
    diameter_open_m: float,
    tip_aero_effectiveness: float,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
) -> tuple[float, float, float]:
    """Annular blade-extension proxy (BEM-lite, not full BEM)."""
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=thrust_scale
    )
    thrust_full_open = _thrust_from_diameter(
        rpm, diameter_open_m, prop_entry, rho=rho, scale=thrust_scale
    )
    increment = max(thrust_full_open - thrust_root, 0.0)

    r_inner = d_root / 2.0
    r_outer = d_geo / 2.0
    r_open = diameter_open_m / 2.0
    denom = r_open**2 - r_inner**2
    if denom <= 0.0 or r_outer <= r_inner:
        annulus_fraction = 0.0
    else:
        annulus_fraction = _clamp01((r_outer**2 - r_inner**2) / denom)

    eff = _clamp01(tip_aero_effectiveness)
    thrust_tip = increment * annulus_fraction * eff
    return thrust_root, thrust_tip, thrust_root + thrust_tip


def _split_calibrated_effective_diameter_delta(
    *,
    rpm: float,
    d_root: float,
    d_aero: float,
    d_open: float,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
) -> tuple[float, float, float]:
    """Calibrated effective-diameter delta (BEM-lite, not full BEM)."""
    from .thrust_split_calibration import (
        resolve_tip_delta_calibration_preset,
        tip_delta_efficiency_factor_for_preset,
    )

    preset = resolve_tip_delta_calibration_preset(config)
    factor = tip_delta_efficiency_factor_for_preset(
        config,
        preset,
        rpm=rpm,
        d_root=d_root,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
    )
    thrust_root, thrust_tip_ideal, _ = _split_effective_diameter_delta(
        rpm=rpm,
        d_root=d_root,
        d_aero=d_aero,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=thrust_scale,
    )
    thrust_tip = thrust_tip_ideal * factor
    return thrust_root, thrust_tip, thrust_root + thrust_tip


@dataclass(frozen=True)
class TipThrustBreakdown:
    """Decomposed tip thrust for activation diagnostics."""

    tip_radial_extension_m: float
    d_tip_equiv_m: float
    geometric_effective_diameter_m: float
    aerodynamic_effective_diameter_m: float
    exposed_tip_fraction: float
    tip_aero_effectiveness: float
    thrust_tip_raw_n: float
    thrust_tip_after_effectiveness_n: float
    thrust_tip_final_n: float


def compute_tip_thrust_breakdown(
    *,
    rpm: float,
    theta_deg: float,
    tip_aero_effectiveness: float,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
) -> TipThrustBreakdown:
    """Expose independent-tip-disk pipeline stages for diagnostic analysis."""
    geometry = config.geometry
    d_root = root_diameter_m(geometry)
    tip_ext = tip_radial_extension_from_config(theta_deg, config)
    d_geo = geometric_effective_diameter_from_config(theta_deg, config)
    eff = _clamp01(tip_aero_effectiveness)
    d_aero = aerodynamic_effective_diameter_m(
        d_geo,
        root_diameter_m=d_root,
        tip_aero_effectiveness=eff,
    )
    length = geometry.tip_segment_length_m
    exposed = _clamp01(tip_ext / length) if length > 0.0 else 0.0
    d_tip_equiv = 2.0 * tip_ext if tip_ext > 0.0 else 0.0
    scale = _thrust_scale(config)
    thrust_raw = _thrust_from_diameter(
        rpm, d_tip_equiv, prop_entry, rho=rho, scale=scale
    )
    thrust_after = _thrust_from_diameter(
        rpm, d_tip_equiv, prop_entry, rho=rho, scale=scale * eff
    )
    return TipThrustBreakdown(
        tip_radial_extension_m=tip_ext,
        d_tip_equiv_m=d_tip_equiv,
        geometric_effective_diameter_m=d_geo,
        aerodynamic_effective_diameter_m=d_aero,
        exposed_tip_fraction=exposed,
        tip_aero_effectiveness=eff,
        thrust_tip_raw_n=thrust_raw,
        thrust_tip_after_effectiveness_n=thrust_after,
        thrust_tip_final_n=thrust_after,
    )


def compute_split_thrust(
    *,
    rpm: float,
    theta_deg: float,
    tip_aero_effectiveness: float,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
    use_legacy_aggregate: bool = False,
    split_mode: ThrustSplitMode | None = None,
) -> SplitThrustResult:
    """Compute root + tip thrust contributions."""
    geometry = config.geometry
    d_root = root_diameter_m(geometry)
    tip_ext = tip_radial_extension_from_config(theta_deg, config)
    d_geo = geometric_effective_diameter_from_config(theta_deg, config)
    eff = _clamp01(tip_aero_effectiveness)
    d_aero = aerodynamic_effective_diameter_m(
        d_geo,
        root_diameter_m=d_root,
        tip_aero_effectiveness=eff,
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

    mode = _resolve_split_mode(config, split_mode)
    scale = _thrust_scale(config)

    if mode == "independent_tip_disk":
        thrust_root, thrust_tip, thrust_total = _split_independent_tip_disk(
            rpm=rpm,
            d_root=d_root,
            tip_ext=tip_ext,
            tip_aero_effectiveness=eff,
            prop_entry=prop_entry,
            rho=rho,
            thrust_scale=scale,
        )
    elif mode == "effective_diameter_delta":
        thrust_root, thrust_tip, thrust_total = _split_effective_diameter_delta(
            rpm=rpm,
            d_root=d_root,
            d_aero=d_aero,
            prop_entry=prop_entry,
            rho=rho,
            thrust_scale=scale,
        )
    elif mode == "annular_extension_proxy":
        thrust_root, thrust_tip, thrust_total = _split_annular_extension_proxy(
            rpm=rpm,
            d_root=d_root,
            d_geo=d_geo,
            diameter_open_m=geometry.diameter_open_m,
            tip_aero_effectiveness=eff,
            prop_entry=prop_entry,
            rho=rho,
            thrust_scale=scale,
        )
    elif mode == "calibrated_effective_diameter_delta":
        thrust_root, thrust_tip, thrust_total = _split_calibrated_effective_diameter_delta(
            rpm=rpm,
            d_root=d_root,
            d_aero=d_aero,
            d_open=geometry.diameter_open_m,
            config=config,
            prop_entry=prop_entry,
            rho=rho,
            thrust_scale=scale,
        )
    else:
        exhaustive: ThrustSplitMode = mode
        raise ValueError(f"Unhandled thrust_split_mode: {exhaustive!r}")

    return SplitThrustResult(
        thrust_root_n=thrust_root,
        thrust_tip_n=thrust_tip,
        thrust_total_n=thrust_total,
        geometric_effective_diameter_m=d_geo,
        aerodynamic_effective_diameter_m=d_aero,
        tip_radial_extension_m=tip_ext,
    )
