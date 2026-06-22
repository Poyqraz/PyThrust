"""Tip-delta efficiency calibration for V2 thrust split (pretest/target calibration)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .calibration import (
    PRETEST_REFERENCE_FRACTION,
    PROJECT_TARGET_FRACTION,
)
from .split_thrust import _thrust_from_diameter, _thrust_scale

TipDeltaCalibrationPreset = Literal[
    "pretest_70_percent",
    "target_85_percent",
    "pretest_70_percent_fixed",
    "target_85_percent_fixed",
]

TIP_DELTA_CALIBRATION_PRESETS: tuple[TipDeltaCalibrationPreset, ...] = (
    "pretest_70_percent",
    "target_85_percent",
    "pretest_70_percent_fixed",
    "target_85_percent_fixed",
)

PRESET_TARGET_RATIOS: dict[TipDeltaCalibrationPreset, float] = {
    "pretest_70_percent": PRETEST_REFERENCE_FRACTION,
    "target_85_percent": PROJECT_TARGET_FRACTION,
    "pretest_70_percent_fixed": PRETEST_REFERENCE_FRACTION,
    "target_85_percent_fixed": PROJECT_TARGET_FRACTION,
}

DEFAULT_CALIBRATION_REFERENCE_CASE_ID = "latch_theta0"


def resolve_tip_delta_calibration_preset(
    config: FoldablePropellerConfig,
) -> TipDeltaCalibrationPreset:
    preset = config.calibration.tip_delta_calibration_preset
    if preset not in PRESET_TARGET_RATIOS:
        raise ValueError(f"Unknown tip_delta_calibration_preset: {preset!r}")
    return preset


def _normalize_fixed_preset(preset: TipDeltaCalibrationPreset) -> TipDeltaCalibrationPreset:
    if preset == "pretest_70_percent":
        return "pretest_70_percent_fixed"
    if preset == "target_85_percent":
        return "target_85_percent_fixed"
    return preset


def required_tip_efficiency_factor(
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
    """Per-case factor needed so T_root + factor×ideal_delta hits target_ratio×T(D_open)."""
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


@dataclass(frozen=True)
class FixedCalibrationFactors:
    reference_case_id: str
    applied_pretest_fixed_factor: float
    applied_target_fixed_factor: float


def compute_fixed_calibration_factors(
    *,
    reference_case_id: str,
    rpm: float,
    d_root: float,
    d_aero_reference: float,
    d_open: float,
    prop_entry: PropellerEntry,
    rho: float,
    thrust_scale: float,
) -> FixedCalibrationFactors:
    """Derive fixed factors from a reference deployment state (default: latch_theta0)."""
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=thrust_scale
    )
    thrust_total_reference = _thrust_from_diameter(
        rpm, d_aero_reference, prop_entry, rho=rho, scale=thrust_scale
    )
    tip_ideal_delta_reference = max(thrust_total_reference - thrust_root, 0.0)
    reference_total = _thrust_from_diameter(
        rpm, d_open, prop_entry, rho=rho, scale=thrust_scale
    )

    pretest_required_tip = max(
        reference_total * PRETEST_REFERENCE_FRACTION - thrust_root, 0.0
    )
    target_required_tip = max(
        reference_total * PROJECT_TARGET_FRACTION - thrust_root, 0.0
    )

    if tip_ideal_delta_reference <= 0.0:
        return FixedCalibrationFactors(
            reference_case_id=reference_case_id,
            applied_pretest_fixed_factor=0.0,
            applied_target_fixed_factor=0.0,
        )

    return FixedCalibrationFactors(
        reference_case_id=reference_case_id,
        applied_pretest_fixed_factor=pretest_required_tip / tip_ideal_delta_reference,
        applied_target_fixed_factor=target_required_tip / tip_ideal_delta_reference,
    )


def applied_fixed_factor_for_preset(
    fixed_factors: FixedCalibrationFactors,
    preset: TipDeltaCalibrationPreset,
) -> float:
    normalized = _normalize_fixed_preset(preset)
    if normalized == "pretest_70_percent_fixed":
        return fixed_factors.applied_pretest_fixed_factor
    return fixed_factors.applied_target_fixed_factor


def tip_delta_efficiency_factor_for_preset(
    config: FoldablePropellerConfig,
    preset: TipDeltaCalibrationPreset,
    *,
    rpm: float,
    d_root: float,
    d_open: float,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
    d_aero_reference: float | None = None,
) -> float:
    """Return the fixed calibration factor for simulation (reference: full-open d_aero)."""
    scale = _thrust_scale(config)
    fixed = compute_fixed_calibration_factors(
        reference_case_id=DEFAULT_CALIBRATION_REFERENCE_CASE_ID,
        rpm=rpm,
        d_root=d_root,
        d_aero_reference=d_aero_reference if d_aero_reference is not None else d_open,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
    )
    return applied_fixed_factor_for_preset(fixed, preset)


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
    pretest_required_tip_efficiency_factor: float
    target_ratio: float
    target_required_total_n: float
    target_required_tip_n: float
    target_required_tip_efficiency_factor: float
    reference_case_id: str
    required_pretest_factor_for_this_case: float
    required_target_factor_for_this_case: float
    applied_pretest_fixed_factor: float
    applied_target_fixed_factor: float
    T_tip_pretest_fixed_n: float
    T_total_pretest_fixed_n: float
    T_tip_target_fixed_n: float
    T_total_target_fixed_n: float
    achieved_pretest_fixed_ratio: float
    achieved_target_fixed_ratio: float
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
            "pretest_required_tip_efficiency_factor": (
                self.pretest_required_tip_efficiency_factor
            ),
            "target_ratio": self.target_ratio,
            "target_required_total_n": self.target_required_total_n,
            "target_required_tip_n": self.target_required_tip_n,
            "target_required_tip_efficiency_factor": (
                self.target_required_tip_efficiency_factor
            ),
            "reference_case_id": self.reference_case_id,
            "required_pretest_factor_for_this_case": (
                self.required_pretest_factor_for_this_case
            ),
            "required_target_factor_for_this_case": (
                self.required_target_factor_for_this_case
            ),
            "applied_pretest_fixed_factor": self.applied_pretest_fixed_factor,
            "applied_target_fixed_factor": self.applied_target_fixed_factor,
            "T_tip_pretest_fixed_n": self.T_tip_pretest_fixed_n,
            "T_total_pretest_fixed_n": self.T_total_pretest_fixed_n,
            "T_tip_target_fixed_n": self.T_tip_target_fixed_n,
            "T_total_target_fixed_n": self.T_total_target_fixed_n,
            "achieved_pretest_fixed_ratio": self.achieved_pretest_fixed_ratio,
            "achieved_target_fixed_ratio": self.achieved_target_fixed_ratio,
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
    fixed_factors: FixedCalibrationFactors,
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

    pretest_ratio = PRETEST_REFERENCE_FRACTION
    target_ratio = PROJECT_TARGET_FRACTION
    pretest_required_total = reference_total * pretest_ratio
    target_required_total = reference_total * target_ratio
    pretest_required_tip = max(pretest_required_total - thrust_root, 0.0)
    target_required_tip = max(target_required_total - thrust_root, 0.0)

    pretest_required_factor = required_tip_efficiency_factor(
        rpm=rpm,
        d_root=d_root,
        d_aero=d_aero,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
        target_ratio=pretest_ratio,
    )
    target_required_factor = required_tip_efficiency_factor(
        rpm=rpm,
        d_root=d_root,
        d_aero=d_aero,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
        target_ratio=target_ratio,
    )

    pretest_fixed = fixed_factors.applied_pretest_fixed_factor
    target_fixed = fixed_factors.applied_target_fixed_factor

    tip_pretest_fixed = tip_ideal_delta * pretest_fixed
    total_pretest_fixed = thrust_root + tip_pretest_fixed
    tip_target_fixed = tip_ideal_delta * target_fixed
    total_target_fixed = thrust_root + tip_target_fixed

    achieved_pretest = (
        total_pretest_fixed / reference_total if reference_total > 0.0 else 0.0
    )
    achieved_target = (
        total_target_fixed / reference_total if reference_total > 0.0 else 0.0
    )

    preset = selected_preset or resolve_tip_delta_calibration_preset(config)
    selected_factor = applied_fixed_factor_for_preset(fixed_factors, preset)
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
        pretest_required_tip_efficiency_factor=pretest_required_factor,
        target_ratio=target_ratio,
        target_required_total_n=target_required_total,
        target_required_tip_n=target_required_tip,
        target_required_tip_efficiency_factor=target_required_factor,
        reference_case_id=fixed_factors.reference_case_id,
        required_pretest_factor_for_this_case=pretest_required_factor,
        required_target_factor_for_this_case=target_required_factor,
        applied_pretest_fixed_factor=pretest_fixed,
        applied_target_fixed_factor=target_fixed,
        T_tip_pretest_fixed_n=tip_pretest_fixed,
        T_total_pretest_fixed_n=total_pretest_fixed,
        T_tip_target_fixed_n=tip_target_fixed,
        T_total_target_fixed_n=total_target_fixed,
        achieved_pretest_fixed_ratio=achieved_pretest,
        achieved_target_fixed_ratio=achieved_target,
        selected_tip_efficiency_factor=selected_factor,
        T_tip_calibrated_n=tip_calibrated,
        T_total_calibrated_n=total_calibrated,
    )
