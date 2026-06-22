"""Sabit referans pervane vs katlanabilir pervane karşılaştırması."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

from pythrust.propellers.database import PropellerEntry

from .integration import (
    post_process_from_operating_point,
    solve_pythrust_operating_point,
)
from .models import FoldablePropellerConfig
from .performance import estimate_foldable_thrust_n, thrust_model_note
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm

COMPARISON_MODEL_NOTE_BASE = (
    "Fixed thrust from PyThrust OperatingPoint (reference propeller Ct/Cp); "
    "same motor/battery/throttle/RPM equilibrium for both"
)
COMPARISON_MODEL_NOTE = COMPARISON_MODEL_NOTE_BASE

COMPARISON_COLUMNS: tuple[str, ...] = (
    "voltage_v",
    "throttle",
    "rpm",
    "fixed_diameter_m",
    "foldable_effective_diameter_m",
    "fixed_thrust_n",
    "foldable_thrust_n",
    "thrust_difference_percent",
    "theta_deg",
    "model_note",
)


@dataclass(frozen=True)
class FixedVsFoldableComparisonRow:
    """Tek throttle noktası için sabit vs katlanabilir karşılaştırma satırı."""

    voltage_v: float
    throttle: float
    rpm: float
    fixed_diameter_m: float
    foldable_effective_diameter_m: float
    fixed_thrust_n: float
    foldable_thrust_n: float
    thrust_difference_percent: float
    theta_deg: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_thrust_difference_percent(
    fixed_thrust_n: float,
    foldable_thrust_n: float,
) -> float:
    """Foldable itkinin sabit referansa göre yüzde farkını hesapla.

    ``((foldable - fixed) / fixed) * 100``
    """
    if fixed_thrust_n <= 0.0:
        return 0.0
    return (foldable_thrust_n - fixed_thrust_n) / fixed_thrust_n * 100.0


def evaluate_fixed_vs_foldable_comparison(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> FixedVsFoldableComparisonRow:
    """Aynı çalışma koşulunda sabit ve katlanabilir sonuçları karşılaştır."""
    operating_point = solve_pythrust_operating_point(
        config,
        prop_entry,
        throttle,
        rho=rho,
        airspeed_mps=airspeed_mps,
    )
    foldable = post_process_from_operating_point(
        operating_point,
        config,
        throttle,
        voltage_v=config.battery.voltage_v,
        rho=rho,
    )

    fixed_thrust_n = operating_point.thrust_n
    d_eff = foldable.effective_diameter_m
    d_ref = config.calibration.reference_diameter_m
    foldable_thrust_n = estimate_foldable_thrust_n(
        config,
        operating_point.rpm,
        d_eff,
        rho=rho,
        fixed_thrust_n=fixed_thrust_n,
        reference_diameter_m=d_ref,
    )

    comparison_note = model_note or (
        f"{COMPARISON_MODEL_NOTE_BASE}; {thrust_model_note(config)}"
    )

    return FixedVsFoldableComparisonRow(
        voltage_v=config.battery.voltage_v,
        throttle=throttle,
        rpm=operating_point.rpm,
        fixed_diameter_m=prop_entry.diameter_m,
        foldable_effective_diameter_m=d_eff,
        fixed_thrust_n=fixed_thrust_n,
        foldable_thrust_n=foldable_thrust_n,
        thrust_difference_percent=compute_thrust_difference_percent(
            fixed_thrust_n,
            foldable_thrust_n,
        ),
        theta_deg=foldable.theta_deg,
        model_note=comparison_note,
    )


def compare_fixed_vs_foldable_sweep(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle_values: Sequence[float],
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> List[FixedVsFoldableComparisonRow]:
    """Birden fazla throttle değeri için karşılaştırma tablosu üret."""
    return [
        evaluate_fixed_vs_foldable_comparison(
            config,
            prop_entry,
            throttle,
            rho=rho,
            airspeed_mps=airspeed_mps,
            model_note=model_note,
        )
        for throttle in throttle_values
    ]
