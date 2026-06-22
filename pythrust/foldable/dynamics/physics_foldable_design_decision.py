"""Decision-oriented variant and deployment comparison for calibrated V2."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from typing import Literal, Sequence

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_from_config,
    root_diameter_m,
)
from ..models import FoldablePropellerConfig
from ..variants import compactness_ratio, make_variant_config, variant_id_from_ratios
from .physics_foldable_performance import (
    FoldableEvaluationContext,
    FoldableThrustEvaluation,
    evaluate_foldable_thrust_at_state,
    resolve_foldable_evaluation_context,
)
from .physics_thrust_split_diagnostic import _run_case_final_state

DecisionLabel = Literal[
    "compact_root_baseline",
    "ideal_upper_bound",
    "current_pretest_candidate",
    "current_target_candidate",
    "latch_required_high_performance",
    "partial_deployment_candidate",
    "not_competitive",
    "",
]

SyntheticCaseKind = Literal["root_only", "fixed_reference"]

DeploymentCaseSpec = tuple[str, float, float, float, float, bool]

FOLDABLE_DESIGN_DECISION_MATRIX_V2_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "case_id",
    "decision_label",
    "theta_final_deg",
    "D_aero_m",
    "T_root_n",
    "T_total_pretest_fixed_n",
    "T_total_target_fixed_n",
    "ratio_to_25cm_pretest",
    "ratio_to_25cm_target",
    "gain_vs_root_pretest_percent",
    "gain_vs_root_target_percent",
    "loss_vs_25cm_pretest_percent",
    "loss_vs_25cm_target_percent",
    "requires_latch_flag",
    "full_open_flag",
    "near_target_flag",
    "compactness_class",
    "deployment_quality_class",
    "engineering_note",
)

FOLDABLE_CANDIDATE_RANKING_V2_COLUMNS: tuple[str, ...] = (
    "rank_pretest",
    "rank_target",
    "variant_id",
    "case_id",
    "T_pretest_n",
    "T_target_n",
    "ratio25_pretest",
    "ratio25_target",
    "gain_vs_root_pretest",
    "gain_vs_root_target",
    "needs_latch",
    "summary_note",
)

DEFAULT_COMPARISON_VARIANT_RATIOS: tuple[tuple[int, int] | None, ...] = (
    None,
    (75, 25),
    (65, 35),
)

SyntheticCaseSpec = tuple[str, SyntheticCaseKind]
SelectedCaseSpec = SyntheticCaseSpec | DeploymentCaseSpec

SELECTED_DEPLOYMENT_CASE_SPECS: tuple[SelectedCaseSpec, ...] = (
    ("root_only_20cm", "root_only"),
    ("fixed_25cm_reference", "fixed_reference"),
    ("latch_theta0", 0.0, 1.0, 1.0, 175.0, True),
    ("bias5_k0.25_s3", 5.0, 0.25, 3.0, 0.0, False),
    ("bias5_k0.25_s5", 5.0, 0.25, 5.0, 0.0, False),
    ("bias10_k0.25_s5", 10.0, 0.25, 5.0, 0.0, False),
)

PRETEST_NEAR_TARGET_RATIO = 0.69
TARGET_NEAR_TARGET_RATIO = 0.84
PARTIAL_COMPETITIVE_PRETEST_RATIO = 0.685
NOT_COMPETITIVE_PRETEST_RATIO = 0.65
FULL_OPEN_D_AERO_TOLERANCE_M = 0.002


def _percent_gain(value: float, baseline: float) -> float:
    if baseline <= 0.0:
        return 0.0
    return 100.0 * (value - baseline) / baseline


@dataclass(frozen=True)
class FoldableDesignDecisionRow:
    variant_id: str
    case_id: str
    decision_label: str
    theta_final_deg: float
    D_aero_m: float
    T_root_n: float
    T_total_pretest_fixed_n: float
    T_total_target_fixed_n: float
    ratio_to_25cm_pretest: float
    ratio_to_25cm_target: float
    gain_vs_root_pretest_percent: float
    gain_vs_root_target_percent: float
    loss_vs_25cm_pretest_percent: float
    loss_vs_25cm_target_percent: float
    requires_latch_flag: bool
    full_open_flag: bool
    near_target_flag: bool
    compactness_class: str
    deployment_quality_class: str
    engineering_note: str

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "variant_id": self.variant_id,
            "case_id": self.case_id,
            "decision_label": self.decision_label,
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "T_root_n": self.T_root_n,
            "T_total_pretest_fixed_n": self.T_total_pretest_fixed_n,
            "T_total_target_fixed_n": self.T_total_target_fixed_n,
            "ratio_to_25cm_pretest": self.ratio_to_25cm_pretest,
            "ratio_to_25cm_target": self.ratio_to_25cm_target,
            "gain_vs_root_pretest_percent": self.gain_vs_root_pretest_percent,
            "gain_vs_root_target_percent": self.gain_vs_root_target_percent,
            "loss_vs_25cm_pretest_percent": self.loss_vs_25cm_pretest_percent,
            "loss_vs_25cm_target_percent": self.loss_vs_25cm_target_percent,
            "requires_latch_flag": self.requires_latch_flag,
            "full_open_flag": self.full_open_flag,
            "near_target_flag": self.near_target_flag,
            "compactness_class": self.compactness_class,
            "deployment_quality_class": self.deployment_quality_class,
            "engineering_note": self.engineering_note,
        }


@dataclass(frozen=True)
class FoldableCandidateRankingRow:
    rank_pretest: int
    rank_target: int
    variant_id: str
    case_id: str
    T_pretest_n: float
    T_target_n: float
    ratio25_pretest: float
    ratio25_target: float
    gain_vs_root_pretest: float
    gain_vs_root_target: float
    needs_latch: bool
    summary_note: str

    def to_csv_row(self) -> dict[str, str | float | int | bool]:
        return {
            "rank_pretest": self.rank_pretest,
            "rank_target": self.rank_target,
            "variant_id": self.variant_id,
            "case_id": self.case_id,
            "T_pretest_n": self.T_pretest_n,
            "T_target_n": self.T_target_n,
            "ratio25_pretest": self.ratio25_pretest,
            "ratio25_target": self.ratio25_target,
            "gain_vs_root_pretest": self.gain_vs_root_pretest,
            "gain_vs_root_target": self.gain_vs_root_target,
            "needs_latch": self.needs_latch,
            "summary_note": self.summary_note,
        }


def resolve_comparison_variants(
    base_config: FoldablePropellerConfig,
    variant_ratios: Sequence[tuple[int, int] | None] = DEFAULT_COMPARISON_VARIANT_RATIOS,
) -> list[tuple[str, FoldablePropellerConfig]]:
    """Build variant list: base config plus RT ratio variants when requested."""
    variants: list[tuple[str, FoldablePropellerConfig]] = []
    seen: set[str] = set()
    for ratio in variant_ratios:
        if ratio is None:
            config = base_config
            variant_id = base_config.id
        else:
            root_ratio, tip_ratio = ratio
            config = make_variant_config(base_config, root_ratio, tip_ratio)
            variant_id = variant_id_from_ratios(root_ratio, tip_ratio)
        if variant_id in seen:
            continue
        seen.add(variant_id)
        variants.append((variant_id, config))
    return variants


def _compactness_class(
    *,
    case_id: str,
    d_aero: float,
    d_root: float,
    d_open: float,
    compactness_ratio_value: float,
) -> str:
    if case_id == "root_only_20cm":
        return "compact_root_only"
    if case_id == "fixed_25cm_reference":
        return "fixed_full_diameter"
    if d_aero >= d_open - FULL_OPEN_D_AERO_TOLERANCE_M:
        return "near_full_open"
    if d_aero <= d_root + 0.005:
        return "compact_root_only"
    if compactness_ratio_value <= 0.75:
        return "compact_foldable"
    return "extended_partial"


def _deployment_quality_class(
    *,
    case_id: str,
    theta_deg: float,
    d_aero: float,
    d_open: float,
    full_open: bool,
) -> str:
    if case_id == "root_only_20cm":
        return "folded_baseline"
    if case_id == "fixed_25cm_reference":
        return "reference_full_open"
    if full_open:
        return "full_open"
    if d_aero >= d_open - 0.005:
        return "near_open"
    if theta_deg <= -90.0:
        return "folded"
    return "partial_equilibrium"


def _is_synthetic_spec(spec: SelectedCaseSpec) -> SyntheticCaseSpec | None:
    if len(spec) == 2 and spec[1] in ("root_only", "fixed_reference"):
        return spec[0], spec[1]  # type: ignore[return-value]
    return None


def _resolve_case_state(
    *,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    spec: SelectedCaseSpec,
    d_root: float,
    d_open: float,
    context: FoldableEvaluationContext,
    constant_rpm: float,
    dt_s: float,
    t_end_s: float,
    rho: float,
) -> tuple[str, float, float, bool, FoldableEvaluationContext]:
    synthetic = _is_synthetic_spec(spec)
    if synthetic is not None:
        case_id, kind = synthetic
        if kind == "root_only":
            return case_id, -180.0, d_root, False, context
        return case_id, 0.0, d_open, False, context

    case_id, bias, k_mult, scale, offset, latch = spec  # type: ignore[misc]
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
    return case_id, theta_final, d_aero, latch, context


def _base_decision_label(
    *,
    case_id: str,
    requires_latch: bool,
    full_open: bool,
    ratio_pretest: float,
    ratio_target: float,
) -> str:
    if case_id == "root_only_20cm":
        return "compact_root_baseline"
    if case_id == "fixed_25cm_reference":
        return "ideal_upper_bound"
    if case_id == "latch_theta0" and requires_latch and full_open:
        return "latch_required_high_performance"
    if (
        not requires_latch
        and case_id.startswith("bias")
        and ratio_pretest >= PARTIAL_COMPETITIVE_PRETEST_RATIO
    ):
        return "partial_deployment_candidate"
    if (
        not requires_latch
        and case_id.startswith("bias")
        and ratio_pretest < NOT_COMPETITIVE_PRETEST_RATIO
    ):
        return "not_competitive"
    if requires_latch and full_open:
        return "latch_required_high_performance"
    return ""


def _apply_anchor_labels(rows: list[FoldableDesignDecisionRow]) -> list[FoldableDesignDecisionRow]:
    """Promote official pretest/target anchors without changing calibration math."""
    updated: list[FoldableDesignDecisionRow] = []
    for row in rows:
        label = row.decision_label
        if row.case_id == "latch_theta0" and row.requires_latch_flag:
            if row.ratio_to_25cm_target >= TARGET_NEAR_TARGET_RATIO:
                label = "current_target_candidate"
            if row.ratio_to_25cm_pretest >= 0.695:
                label = "current_pretest_candidate"
        updated.append(replace(row, decision_label=label))

    best_partial: FoldableDesignDecisionRow | None = None
    for row in updated:
        if row.case_id.startswith("bias") and not row.requires_latch_flag:
            if (
                best_partial is None
                or row.ratio_to_25cm_pretest > best_partial.ratio_to_25cm_pretest
            ):
                best_partial = row

    if best_partial is None:
        return updated

    result: list[FoldableDesignDecisionRow] = []
    for row in updated:
        label = row.decision_label
        if (
            row.variant_id == best_partial.variant_id
            and row.case_id == best_partial.case_id
            and label not in (
                "compact_root_baseline",
                "ideal_upper_bound",
                "current_pretest_candidate",
            )
        ):
            label = "partial_deployment_candidate"
        result.append(replace(row, decision_label=label))
    return result


def _engineering_note(
    *,
    case_id: str,
    variant_id: str,
    requires_latch: bool,
    full_open: bool,
    ratio_pretest: float,
    ratio_target: float,
    compactness_class: str,
) -> str:
    if case_id == "root_only_20cm":
        return "Compact 20 cm root disk; zero tip extension baseline"
    if case_id == "fixed_25cm_reference":
        return "Non-foldable 25 cm reference at 100% thrust recovery"
    if case_id == "latch_theta0":
        return (
            f"Latch capture to theta=0 on {variant_id}; "
            f"pretest {ratio_pretest:.1%}, target {ratio_target:.1%} of 25 cm"
        )
    latch_note = "requires latch" if requires_latch else "free equilibrium"
    open_note = "full open" if full_open else "partial deployment"
    return (
        f"{variant_id} {case_id}: {open_note}, {latch_note}; "
        f"pretest {ratio_pretest:.1%}, target {ratio_target:.1%}; "
        f"{compactness_class}"
    )


def run_foldable_design_decision_matrix_v2(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    variant_ratios: Sequence[tuple[int, int] | None] = DEFAULT_COMPARISON_VARIANT_RATIOS,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    rho: float = 1.225,
) -> list[FoldableDesignDecisionRow]:
    """Build decision matrix rows for each variant and selected deployment case."""
    all_rows: list[FoldableDesignDecisionRow] = []

    for variant_id, config in resolve_comparison_variants(base_config, variant_ratios):
        context = resolve_foldable_evaluation_context(
            config,
            prop_entry,
            dt_s=dt_s,
            t_end_s=t_end_s,
            constant_rpm=constant_rpm,
            rho=rho,
        )
        d_root = context.d_root_m
        d_open = context.d_open_m
        compactness = compactness_ratio(config)

        variant_rows: list[FoldableDesignDecisionRow] = []
        for spec in SELECTED_DEPLOYMENT_CASE_SPECS:
            case_id, theta, d_aero, requires_latch, ctx = _resolve_case_state(
                config=config,
                prop_entry=prop_entry,
                spec=spec,
                d_root=d_root,
                d_open=d_open,
                context=context,
                constant_rpm=constant_rpm,
                dt_s=dt_s,
                t_end_s=t_end_s,
                rho=rho,
            )
            thrust = evaluate_foldable_thrust_at_state(
                d_aero=d_aero,
                context=ctx,
                prop_entry=prop_entry,
                rpm=constant_rpm,
                rho=rho,
            )
            if case_id == "fixed_25cm_reference":
                reference_total = ctx.reference_total_25cm_n
                thrust = FoldableThrustEvaluation(
                    T_root_n=thrust.T_root_n,
                    T_tip_ideal_delta_n=reference_total - thrust.T_root_n,
                    T_total_ideal_delta_n=reference_total,
                    T_tip_pretest_fixed_n=reference_total - thrust.T_root_n,
                    T_total_pretest_fixed_n=reference_total,
                    pretest_fixed_ratio_to_25cm=1.0,
                    T_tip_target_fixed_n=reference_total - thrust.T_root_n,
                    T_total_target_fixed_n=reference_total,
                    target_fixed_ratio_to_25cm=1.0,
                    gain_vs_root_pretest_percent=_percent_gain(
                        reference_total, ctx.T_root_baseline_n
                    ),
                    gain_vs_root_target_percent=_percent_gain(
                        reference_total, ctx.T_root_baseline_n
                    ),
                    loss_vs_25cm_pretest_percent=0.0,
                    loss_vs_25cm_target_percent=0.0,
                )
            full_open = d_aero >= d_open - FULL_OPEN_D_AERO_TOLERANCE_M
            near_target = (
                thrust.pretest_fixed_ratio_to_25cm >= PRETEST_NEAR_TARGET_RATIO
                or thrust.target_fixed_ratio_to_25cm >= TARGET_NEAR_TARGET_RATIO
            )
            compact_class = _compactness_class(
                case_id=case_id,
                d_aero=d_aero,
                d_root=d_root,
                d_open=d_open,
                compactness_ratio_value=compactness,
            )
            deploy_class = _deployment_quality_class(
                case_id=case_id,
                theta_deg=theta,
                d_aero=d_aero,
                d_open=d_open,
                full_open=full_open,
            )
            ratio_pretest = thrust.pretest_fixed_ratio_to_25cm
            ratio_target = thrust.target_fixed_ratio_to_25cm
            variant_rows.append(
                FoldableDesignDecisionRow(
                    variant_id=variant_id,
                    case_id=case_id,
                    decision_label=_base_decision_label(
                        case_id=case_id,
                        requires_latch=requires_latch,
                        full_open=full_open,
                        ratio_pretest=ratio_pretest,
                        ratio_target=ratio_target,
                    ),
                    theta_final_deg=theta,
                    D_aero_m=d_aero,
                    T_root_n=thrust.T_root_n,
                    T_total_pretest_fixed_n=thrust.T_total_pretest_fixed_n,
                    T_total_target_fixed_n=thrust.T_total_target_fixed_n,
                    ratio_to_25cm_pretest=ratio_pretest,
                    ratio_to_25cm_target=ratio_target,
                    gain_vs_root_pretest_percent=thrust.gain_vs_root_pretest_percent,
                    gain_vs_root_target_percent=thrust.gain_vs_root_target_percent,
                    loss_vs_25cm_pretest_percent=thrust.loss_vs_25cm_pretest_percent,
                    loss_vs_25cm_target_percent=thrust.loss_vs_25cm_target_percent,
                    requires_latch_flag=requires_latch,
                    full_open_flag=full_open,
                    near_target_flag=near_target,
                    compactness_class=compact_class,
                    deployment_quality_class=deploy_class,
                    engineering_note=_engineering_note(
                        case_id=case_id,
                        variant_id=variant_id,
                        requires_latch=requires_latch,
                        full_open=full_open,
                        ratio_pretest=ratio_pretest,
                        ratio_target=ratio_target,
                        compactness_class=compact_class,
                    ),
                )
            )
        all_rows.extend(_apply_anchor_labels(variant_rows))

    return all_rows


def run_foldable_candidate_ranking_v2(
    decision_rows: Sequence[FoldableDesignDecisionRow],
) -> list[FoldableCandidateRankingRow]:
    """Rank deployable candidates by pretest and target calibrated thrust."""
    rankable = [
        row
        for row in decision_rows
        if row.case_id not in ("root_only_20cm", "fixed_25cm_reference")
    ]
    by_pretest = sorted(
        rankable,
        key=lambda row: row.T_total_pretest_fixed_n,
        reverse=True,
    )
    by_target = sorted(
        rankable,
        key=lambda row: row.T_total_target_fixed_n,
        reverse=True,
    )
    pretest_rank = {
        (row.variant_id, row.case_id): index + 1
        for index, row in enumerate(by_pretest)
    }
    target_rank = {
        (row.variant_id, row.case_id): index + 1
        for index, row in enumerate(by_target)
    }

    rows: list[FoldableCandidateRankingRow] = []
    for row in rankable:
        key = (row.variant_id, row.case_id)
        latch_note = "latch" if row.requires_latch_flag else "no latch"
        rows.append(
            FoldableCandidateRankingRow(
                rank_pretest=pretest_rank[key],
                rank_target=target_rank[key],
                variant_id=row.variant_id,
                case_id=row.case_id,
                T_pretest_n=row.T_total_pretest_fixed_n,
                T_target_n=row.T_total_target_fixed_n,
                ratio25_pretest=row.ratio_to_25cm_pretest,
                ratio25_target=row.ratio_to_25cm_target,
                gain_vs_root_pretest=row.gain_vs_root_pretest_percent,
                gain_vs_root_target=row.gain_vs_root_target_percent,
                needs_latch=row.requires_latch_flag,
                summary_note=(
                    f"{row.decision_label or 'evaluated'}; "
                    f"{latch_note}; pretest rank {pretest_rank[key]}"
                ),
            )
        )
    rows.sort(key=lambda item: (item.rank_pretest, item.variant_id, item.case_id))
    return rows


def write_foldable_design_decision_matrix_v2_csv(
    path: str,
    rows: Sequence[FoldableDesignDecisionRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(FOLDABLE_DESIGN_DECISION_MATRIX_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_foldable_candidate_ranking_v2_csv(
    path: str,
    rows: Sequence[FoldableCandidateRankingRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(FOLDABLE_CANDIDATE_RANKING_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
