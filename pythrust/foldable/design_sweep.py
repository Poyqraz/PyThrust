"""Tasarım varyantı sweep — kök/uç oranı karşılaştırması."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pythrust.propellers.database import PropellerEntry

from .comparison import (
    COMPARISON_MODEL_NOTE_BASE,
    compute_thrust_difference_percent,
)
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm
from .integration import solve_pythrust_operating_point
from .models import FoldablePropellerConfig
from .performance import estimate_foldable_thrust_n, thrust_model_note
from .variants import (
    DEFAULT_ROOT_TIP_RATIOS,
    compactness_ratio,
    make_variant_config,
)

DESIGN_VARIANT_SWEEP_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "voltage_v",
    "throttle",
    "rpm",
    "theta_deg",
    "effective_diameter_m",
    "fixed_thrust_n",
    "foldable_thrust_n",
    "thrust_difference_percent",
    "compactness_ratio",
    "model_note",
)

DESIGN_VARIANT_MODEL_NOTE = (
    "Parametric root/tip ratio sweep; reference_scaled thrust; "
    "compactness_ratio = folded_effective_diameter / open_diameter"
)


@dataclass(frozen=True)
class DesignVariantSweepRow:
    """Tek varyant + throttle için tasarım karşılaştırma satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    voltage_v: float
    throttle: float
    rpm: float
    theta_deg: float
    effective_diameter_m: float
    fixed_thrust_n: float
    foldable_thrust_n: float
    thrust_difference_percent: float
    compactness_ratio: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_design_variant_row(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    root_ratio: int,
    tip_ratio: int,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> DesignVariantSweepRow:
    """Tek varyant ve throttle için sweep satırı üret."""
    operating_point = solve_pythrust_operating_point(
        config,
        prop_entry,
        throttle,
        rho=rho,
        airspeed_mps=airspeed_mps,
    )
    rpm = operating_point.rpm
    theta_deg = theta_deg_from_rpm(rpm, config)
    d_eff = effective_diameter_m(theta_deg, config)
    fixed_thrust_n = operating_point.thrust_n
    foldable_thrust_n = estimate_foldable_thrust_n(
        config,
        rpm,
        d_eff,
        rho=rho,
        fixed_thrust_n=fixed_thrust_n,
        reference_diameter_m=config.calibration.reference_diameter_m,
    )

    note = model_note or (
        f"{DESIGN_VARIANT_MODEL_NOTE}; {COMPARISON_MODEL_NOTE_BASE}; "
        f"{thrust_model_note(config)}"
    )

    return DesignVariantSweepRow(
        variant_id=config.id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        voltage_v=config.battery.voltage_v,
        throttle=throttle,
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=d_eff,
        fixed_thrust_n=fixed_thrust_n,
        foldable_thrust_n=foldable_thrust_n,
        thrust_difference_percent=compute_thrust_difference_percent(
            fixed_thrust_n,
            foldable_thrust_n,
        ),
        compactness_ratio=compactness_ratio(config),
        model_note=note,
    )


def sweep_design_variants(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle_values: Sequence[float],
    *,
    ratios: Sequence[Tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
) -> List[DesignVariantSweepRow]:
    """Tüm varyantlar ve throttle noktaları için sweep tablosu."""
    rows: List[DesignVariantSweepRow] = []
    for root_ratio, tip_ratio in ratios:
        variant_config = make_variant_config(base_config, root_ratio, tip_ratio)
        for throttle in throttle_values:
            rows.append(
                evaluate_design_variant_row(
                    variant_config,
                    prop_entry,
                    throttle,
                    root_ratio=root_ratio,
                    tip_ratio=tip_ratio,
                    rho=rho,
                    airspeed_mps=airspeed_mps,
                )
            )
    return rows
