"""Foldable V2 thrust evaluation against root, ideal, and calibrated references."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Literal, Sequence

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_from_config,
    root_diameter_m,
)
from ..models import FoldablePropellerConfig
from .physics_thrust_split_diagnostic import _run_case_final_state
from .split_thrust import _thrust_from_diameter, _thrust_scale
from .thrust_split_calibration import (
    DEFAULT_CALIBRATION_REFERENCE_CASE_ID,
    FixedCalibrationFactors,
    compute_fixed_calibration_factors,
)

ThrustModelLevel = Literal[
    "root_only",
    "ideal_effective_delta",
    "pretest_70_fixed",
    "target_85_fixed",
    "reference_25cm",
]

DecisionLabel = Literal[
    "compact_root_baseline",
    "fixed_reference",
    "ideal_upper_bound",
    "current_pretest_candidate",
    "target_candidate",
]

FOLDABLE_PERFORMANCE_SUMMARY_V2_COLUMNS: tuple[str, ...] = (
    "case_id",
    "decision_label",
    "theta_final_deg",
    "D_aero_m",
    "thrust_model_level",
    "T_total_n",
    "ratio_to_25cm_reference",
    "gain_vs_root_percent",
    "compactness_note",
    "mechanism_note",
    "calibration_note",
)


@dataclass(frozen=True)
class FoldableEvaluationContext:
    """Shared baselines and fixed calibration factors for V2 evaluation."""

    fixed_factors: FixedCalibrationFactors
    d_root_m: float
    d_open_m: float
    reference_total_25cm_n: float
    T_root_baseline_n: float
    thrust_scale: float


@dataclass(frozen=True)
class FoldableThrustEvaluation:
    T_root_n: float
    T_tip_ideal_delta_n: float
    T_total_ideal_delta_n: float
    T_tip_pretest_fixed_n: float
    T_total_pretest_fixed_n: float
    pretest_fixed_ratio_to_25cm: float
    T_tip_target_fixed_n: float
    T_total_target_fixed_n: float
    target_fixed_ratio_to_25cm: float
    gain_vs_root_pretest_percent: float
    gain_vs_root_target_percent: float
    loss_vs_25cm_pretest_percent: float
    loss_vs_25cm_target_percent: float


@dataclass(frozen=True)
class FoldablePerformanceSummaryRow:
    case_id: str
    decision_label: str
    theta_final_deg: float
    D_aero_m: float
    thrust_model_level: str
    T_total_n: float
    ratio_to_25cm_reference: float
    gain_vs_root_percent: float
    compactness_note: str
    mechanism_note: str
    calibration_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "decision_label": self.decision_label,
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "thrust_model_level": self.thrust_model_level,
            "T_total_n": self.T_total_n,
            "ratio_to_25cm_reference": self.ratio_to_25cm_reference,
            "gain_vs_root_percent": self.gain_vs_root_percent,
            "compactness_note": self.compactness_note,
            "mechanism_note": self.mechanism_note,
            "calibration_note": self.calibration_note,
        }


def _percent_gain(value: float, baseline: float) -> float:
    if baseline <= 0.0:
        return 0.0
    return 100.0 * (value - baseline) / baseline


def _percent_loss(reference: float, value: float) -> float:
    if reference <= 0.0:
        return 0.0
    return 100.0 * (reference - value) / reference


def evaluate_foldable_thrust_at_state(
    *,
    d_aero: float,
    context: FoldableEvaluationContext,
    prop_entry: PropellerEntry,
    rpm: float,
    rho: float = 1.225,
) -> FoldableThrustEvaluation:
    """Ideal and calibrated thrust levels at one deployment state."""
    scale = context.thrust_scale
    d_root = context.d_root_m
    thrust_root = _thrust_from_diameter(
        rpm, d_root, prop_entry, rho=rho, scale=scale
    )
    thrust_total_ideal = _thrust_from_diameter(
        rpm, d_aero, prop_entry, rho=rho, scale=scale
    )
    tip_ideal_delta = max(thrust_total_ideal - thrust_root, 0.0)
    total_ideal = thrust_root + tip_ideal_delta

    pretest_fixed = context.fixed_factors.applied_pretest_fixed_factor
    target_fixed = context.fixed_factors.applied_target_fixed_factor
    tip_pretest = tip_ideal_delta * pretest_fixed
    total_pretest = thrust_root + tip_pretest
    tip_target = tip_ideal_delta * target_fixed
    total_target = thrust_root + tip_target

    reference = context.reference_total_25cm_n
    root_baseline = context.T_root_baseline_n

    return FoldableThrustEvaluation(
        T_root_n=thrust_root,
        T_tip_ideal_delta_n=tip_ideal_delta,
        T_total_ideal_delta_n=total_ideal,
        T_tip_pretest_fixed_n=tip_pretest,
        T_total_pretest_fixed_n=total_pretest,
        pretest_fixed_ratio_to_25cm=(
            total_pretest / reference if reference > 0.0 else 0.0
        ),
        T_tip_target_fixed_n=tip_target,
        T_total_target_fixed_n=total_target,
        target_fixed_ratio_to_25cm=(
            total_target / reference if reference > 0.0 else 0.0
        ),
        gain_vs_root_pretest_percent=_percent_gain(total_pretest, root_baseline),
        gain_vs_root_target_percent=_percent_gain(total_target, root_baseline),
        loss_vs_25cm_pretest_percent=_percent_loss(reference, total_pretest),
        loss_vs_25cm_target_percent=_percent_loss(reference, total_target),
    )


def resolve_foldable_evaluation_context(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    rho: float = 1.225,
    reference_case_id: str = DEFAULT_CALIBRATION_REFERENCE_CASE_ID,
) -> FoldableEvaluationContext:
    """Derive fixed calibration factors from the latch_theta0 reference case."""
    d_root = root_diameter_m(config.geometry)
    d_open = config.geometry.diameter_open_m
    scale = _thrust_scale(config)

    theta_ref, tip_eff_ref = _run_case_final_state(
        config,
        prop_entry,
        case_id=reference_case_id,
        deployment_bias_angle_deg=0.0,
        stiffness_multiplier=1.0,
        cent_moment_geometry_scale=1.0,
        initial_stow_offset_deg=175.0,
        open_latch_diagnostic=True,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
    )
    d_geo_ref = geometric_effective_diameter_from_config(theta_ref, config)
    d_aero_ref = aerodynamic_effective_diameter_m(
        d_geo_ref,
        root_diameter_m=d_root,
        tip_aero_effectiveness=tip_eff_ref,
    )
    fixed_factors = compute_fixed_calibration_factors(
        reference_case_id=reference_case_id,
        rpm=constant_rpm,
        d_root=d_root,
        d_aero_reference=d_aero_ref,
        d_open=d_open,
        prop_entry=prop_entry,
        rho=rho,
        thrust_scale=scale,
    )
    reference_total = _thrust_from_diameter(
        constant_rpm, d_open, prop_entry, rho=rho, scale=scale
    )
    root_baseline = _thrust_from_diameter(
        constant_rpm, d_root, prop_entry, rho=rho, scale=scale
    )
    return FoldableEvaluationContext(
        fixed_factors=fixed_factors,
        d_root_m=d_root,
        d_open_m=d_open,
        reference_total_25cm_n=reference_total,
        T_root_baseline_n=root_baseline,
        thrust_scale=scale,
    )


def _summary_row(
    *,
    case_id: str,
    decision_label: str,
    theta_final_deg: float,
    d_aero_m: float,
    thrust_model_level: ThrustModelLevel,
    T_total_n: float,
    context: FoldableEvaluationContext,
    compactness_note: str,
    mechanism_note: str,
    calibration_note: str,
) -> FoldablePerformanceSummaryRow:
    reference = context.reference_total_25cm_n
    return FoldablePerformanceSummaryRow(
        case_id=case_id,
        decision_label=decision_label,
        theta_final_deg=theta_final_deg,
        D_aero_m=d_aero_m,
        thrust_model_level=thrust_model_level,
        T_total_n=T_total_n,
        ratio_to_25cm_reference=T_total_n / reference if reference > 0.0 else 0.0,
        gain_vs_root_percent=_percent_gain(T_total_n, context.T_root_baseline_n),
        compactness_note=compactness_note,
        mechanism_note=mechanism_note,
        calibration_note=calibration_note,
    )


def run_foldable_performance_summary_v2(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    context: FoldableEvaluationContext | None = None,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    rho: float = 1.225,
) -> list[FoldablePerformanceSummaryRow]:
    """Compact engineering summary for selected foldable evaluation cases."""
    eval_context = context or resolve_foldable_evaluation_context(
        config,
        prop_entry,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
        rho=rho,
    )
    d_root = eval_context.d_root_m
    d_open = eval_context.d_open_m
    ref_case = eval_context.fixed_factors.reference_case_id
    cal_note = (
        f"Fixed factors from {ref_case}: "
        f"pretest={eval_context.fixed_factors.applied_pretest_fixed_factor:.4f}, "
        f"target={eval_context.fixed_factors.applied_target_fixed_factor:.4f}"
    )

    rows: list[FoldablePerformanceSummaryRow] = []

    root_eval = evaluate_foldable_thrust_at_state(
        d_aero=d_root,
        context=eval_context,
        prop_entry=prop_entry,
        rpm=constant_rpm,
        rho=rho,
    )
    rows.append(
        _summary_row(
            case_id="root_only_20cm",
            decision_label="compact_root_baseline",
            theta_final_deg=-180.0,
            d_aero_m=d_root,
            thrust_model_level="root_only",
            T_total_n=root_eval.T_root_n,
            context=eval_context,
            compactness_note="Folded root disk only; D_aero = D_root = 0.20 m",
            mechanism_note="No tip extension; compact stowed envelope",
            calibration_note="Uncalibrated root-only actuator disk",
        )
    )

    ref_eval = evaluate_foldable_thrust_at_state(
        d_aero=d_open,
        context=eval_context,
        prop_entry=prop_entry,
        rpm=constant_rpm,
        rho=rho,
    )
    rows.append(
        _summary_row(
            case_id="fixed_25cm_reference",
            decision_label="fixed_reference",
            theta_final_deg=0.0,
            d_aero_m=d_open,
            thrust_model_level="reference_25cm",
            T_total_n=eval_context.reference_total_25cm_n,
            context=eval_context,
            compactness_note="Full 25 cm fixed reference propeller",
            mechanism_note="Non-foldable 25 cm benchmark at 7100 rpm",
            calibration_note="Ct×ρ×n²×D_open⁴ baseline (100%)",
        )
    )

    deployment_specs: tuple[tuple[str, float, float, float, float, bool], ...] = (
        ("latch_theta0", 0.0, 1.0, 1.0, 175.0, True),
        ("bias5_k0.25_s3", 5.0, 0.25, 3.0, 0.0, False),
        ("bias5_k0.25_s5", 5.0, 0.25, 5.0, 0.0, False),
        ("bias10_k0.25_s5", 10.0, 0.25, 5.0, 0.0, False),
    )

    for case_id, bias, k_mult, scale, offset, latch in deployment_specs:
        theta_final, tip_eff = _run_case_final_state(
            config,
            prop_entry,
            case_id=case_id,
            deployment_bias_angle_deg=bias,
            stiffness_multiplier=k_mult,
            cent_moment_geometry_scale=scale,
            initial_stow_offset_deg=offset,
            open_latch_diagnostic=latch,
            dt_s=dt_s,
            t_end_s=t_end_s,
            constant_rpm=constant_rpm,
        )
        d_geo = geometric_effective_diameter_from_config(theta_final, config)
        d_aero = aerodynamic_effective_diameter_m(
            d_geo,
            root_diameter_m=d_root,
            tip_aero_effectiveness=tip_eff,
        )
        thrust_eval = evaluate_foldable_thrust_at_state(
            d_aero=d_aero,
            context=eval_context,
            prop_entry=prop_entry,
            rpm=constant_rpm,
            rho=rho,
        )
        mechanism = (
            f"bias={bias:g}°, k×={k_mult:g}, scale={scale:g}, "
            f"offset={offset:g}°, latch={latch}"
        )
        compactness = f"D_aero={d_aero:.4f} m vs D_root={d_root:.2f} m"

        level_specs: tuple[tuple[ThrustModelLevel, float, str], ...] = (
            (
                "ideal_effective_delta",
                thrust_eval.T_total_ideal_delta_n,
                "ideal_upper_bound" if case_id == "latch_theta0" else "",
            ),
            (
                "pretest_70_fixed",
                thrust_eval.T_total_pretest_fixed_n,
                "current_pretest_candidate" if case_id == "latch_theta0" else "",
            ),
            (
                "target_85_fixed",
                thrust_eval.T_total_target_fixed_n,
                "target_candidate" if case_id == "latch_theta0" else "",
            ),
        )
        for level, total_n, label in level_specs:
            rows.append(
                _summary_row(
                    case_id=case_id,
                    decision_label=label,
                    theta_final_deg=theta_final,
                    d_aero_m=d_aero,
                    thrust_model_level=level,
                    T_total_n=total_n,
                    context=eval_context,
                    compactness_note=compactness,
                    mechanism_note=mechanism,
                    calibration_note=cal_note,
                )
            )

    return rows


def write_foldable_performance_summary_v2_csv(
    path: str,
    rows: Sequence[FoldablePerformanceSummaryRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(FOLDABLE_PERFORMANCE_SUMMARY_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
