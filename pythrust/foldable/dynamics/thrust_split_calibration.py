"""Tip-delta efficiency calibration for V2 thrust split (TÜBİTAK pretest/target)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .calibration import (
    TUBITAK_LIFT_REFERENCE_FRACTION,
    TUBITAK_LIFT_TARGET_FRACTION,
    TUBITAK_OPEN_DIAMETER_M,
)
from .split_thrust import _thrust_from_diameter, _thrust_scale

TipDeltaCalibrationPreset = Literal["pretest_70_percent", "target_85_percent"]

TIP_DELTA_CALIBRATION_PRESETS: tuple[TipDeltaCalibrationPreset, ...] = (
    "pretest_70_percent",
    "target_85_percent",
)

PRESET_TARGET_RATIOS: dict[TipDeltaCalibrationPreset, float] = {
    "pretest_70_percent": TUBITAK_LIFT_REFERENCE_FRACTION,
    "target_85_percent": TUBITAK_LIFT_TARGET_FRACTION,
}


def resolve_tip_delta_calibration_preset(
    config: FoldablePropellerConfig,
) -> TipDeltaCalibrationPreset:
    preset = config.calibration.tip_delta_calibration_preset
    if preset not in PRESET_TARGET_RATIOS:
        raise ValueError(f"Unknown tip_delta_calibration_preset: {preset!r}")
    return preset


def tip_delta_efficiency_factor(
    *,
    rpm: float,
    d_root: float,
    d_aero: float,
    d_open: float,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
    target_ratio: float,
) -> float:
    """Efficiency factor so T_root + factor×ideal_delta hits target_ratio×T(D_open).

    Uses the ideal tip delta at the supplied ``d_aero`` state:
    ``required_tip = max(target_ratio × T(D_open) − T_root, 0)``.
    """
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=thrust_scale
    )
    thrust_total_ideal = _thrust_from_diameter(
        rpm, d_aero, prop_entry, rho=rho, scale=thrust_scale
    )
    tip_ideal_delta = max(thrust_total_ideal - thrust_root, 0.0)
    reference_total = _thrust_from_diameter(
        rpm, d_open, prop_entry, rho=rho, scale=thrust_scale
    )
    target_total = reference_total * target_ratio
    required_tip = max(target_total - thrust_root, 0.0)
    if tip_ideal_delta <= 0.0:
        return 0.0
    return required_tip / tip_ideal_delta


def tip_delta_efficiency_factor_for_preset(
    config: FoldablePropellerConfig,
    preset: TipDeltaCalibrationPreset,
    *,
    rpm: float,
    d_root: float,
    d_open: float,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
) -> float:
    """Preset factor at full-open reference (d_aero = d_open) for simulation use."""
    scale = _thrust_scale(config)
    return tip_delta_efficiency_factor(
        rpm=rpm,
        d_root=d_root,
        d_aero=d_open,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
        target_ratio=PRESET_TARGET_RATIOS[preset],
    )


@dataclass(frozen=True)
class CalibratedThrustSplitDiagnostics:
    case_id: str
    D_root_m: float
    D_aero_m: float
    D_open_m: float
    T_root_n: float
    T_tip_ideal_delta_n: float
    T_total_ideal_n: float
    reference_total_25cm_n: float
    pretest_ratio: float
    pretest_required_total_n: float
    pretest_required_tip_n: float
    pretest_tip_efficiency_factor: float
    target_ratio: float
    target_required_total_n: float
    target_required_tip_n: float
    target_tip_efficiency_factor: float
    selected_tip_efficiency_factor: float
    T_tip_calibrated_n: float
    T_total_calibrated_n: float

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "D_root_m": self.D_root_m,
            "D_aero_m": self.D_aero_m,
            "D_open_m": self.D_open_m,
            "T_root_n": self.T_root_n,
            "T_tip_ideal_delta_n": self.T_tip_ideal_delta_n,
            "T_total_ideal_n": self.T_total_ideal_n,
            "reference_total_25cm_n": self.reference_total_25cm_n,
            "pretest_ratio": self.pretest_ratio,
            "pretest_required_total_n": self.pretest_required_total_n,
            "pretest_required_tip_n": self.pretest_required_tip_n,
            "pretest_tip_efficiency_factor": self.pretest_tip_efficiency_factor,
            "target_ratio": self.target_ratio,
            "target_required_total_n": self.target_required_total_n,
            "target_required_tip_n": self.target_required_tip_n,
            "target_tip_efficiency_factor": self.target_tip_efficiency_factor,
            "selected_tip_efficiency_factor": self.selected_tip_efficiency_factor,
            "T_tip_calibrated_n": self.T_tip_calibrated_n,
            "T_total_calibrated_n": self.T_total_calibrated_n,
        }


def compute_calibrated_thrust_split_diagnostics(
    *,
    case_id: str,
    rpm: float,
    d_root: float,
    d_aero: float,
    d_open: float,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
    selected_preset: TipDeltaCalibrationPreset | None = None,
) -> CalibratedThrustSplitDiagnostics:
    """Full calibration breakdown for one deployment state."""
    scale = _thrust_scale(config)
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=scale
    )
    thrust_total_ideal = _thrust_from_diameter(
        rpm, d_aero, prop_entry, rho=rho, scale=scale
    )
    tip_ideal_delta = max(thrust_total_ideal - thrust_root, 0.0)
    reference_total = _thrust_from_diameter(
        rpm, d_open, prop_entry, rho=rho, scale=scale
    )

    pretest_ratio = TUBITAK_LIFT_REFERENCE_FRACTION
    target_ratio = TUBITAK_LIFT_TARGET_FRACTION
    pretest_required_total = reference_total * pretest_ratio
    target_required_total = reference_total * target_ratio
    pretest_required_tip = max(pretest_required_total - thrust_root, 0.0)
    target_required_tip = max(target_required_total - thrust_root, 0.0)

    pretest_factor = (
        tip_delta_efficiency_factor(
            rpm=rpm,
            d_root=d_root,
            d_aero=d_aero,
            d_open=d_open,
            prop_entry=prop_entry,
            rho=rho,
            thrust_scale=scale,
            target_ratio=pretest_ratio,
        )
    )
    target_factor = tip_delta_efficiency_factor(
        rpm=rpm,
        d_root=d_root,
        d_aero=d_aero,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
        target_ratio=target_ratio,
    )

    preset = selected_preset or resolve_tip_delta_calibration_preset(config)
    if preset == "pretest_70_percent":
        selected_factor = pretest_factor
    else:
        selected_factor = target_factor

    tip_calibrated = tip_ideal_delta * selected_factor
    total_calibrated = thrust_root + tip_calibrated

    return CalibratedThrustSplitDiagnostics(
        case_id=case_id,
        D_root_m=d_root,
        D_aero_m=d_aero,
        D_open_m=d_open,
        T_root_n=thrust_root,
        T_tip_ideal_delta_n=tip_ideal_delta,
        T_total_ideal_n=thrust_root + tip_ideal_delta,
        reference_total_25cm_n=reference_total,
        pretest_ratio=pretest_ratio,
        pretest_required_total_n=pretest_required_total,
        pretest_required_tip_n=pretest_required_tip,
        pretest_tip_efficiency_factor=pretest_factor,
        target_ratio=target_ratio,
        target_required_total_n=target_required_total,
        target_required_tip_n=target_required_tip,
        target_tip_efficiency_factor=target_factor,
        selected_tip_efficiency_factor=selected_factor,
        T_tip_calibrated_n=tip_calibrated,
        T_total_calibrated_n=total_calibrated,
    )
