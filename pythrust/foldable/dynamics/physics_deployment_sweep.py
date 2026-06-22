"""Deployment bias × stiffness × moment-scale diagnostic sweep."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from .aero_effectiveness import deployment_progress_from_theta
from ..models import FoldablePropellerConfig
from .physics_foldable_performance import (
    FoldableEvaluationContext,
    FoldableThrustEvaluation,
    evaluate_foldable_thrust_at_state,
    resolve_foldable_evaluation_context,
)
from .physics_stability import analyze_physics_stability
from .physics_simulation import run_prescribed_rpm_physics
from .prescribed_rpm import PrescribedRpmConfig
from .tip_aero_effectiveness import geometric_tip_exposure_01

MEANINGFUL_DEPLOYMENT_PROGRESS = 0.5
MEANINGFUL_D_AERO_M = 0.22

DEPLOYMENT_BIAS_STIFFNESS_SWEEP_COLUMNS: tuple[str, ...] = (
    "case_id",
    "bias_deg",
    "stiffness_multiplier",
    "moment_scale",
    "theta_final_deg",
    "deployment_progress_final",
    "D_geo_final_m",
    "D_aero_final_m",
    "thrust_root_final_n",
    "thrust_tip_final_n",
    "thrust_total_final_n",
    "tip_aero_effectiveness_final",
    "hinge_state",
    "stable_flag",
    "reaches_meaningful_deployment_flag",
    "reaches_open_stop_flag",
    "open_latch_diagnostic",
    "T_root_n",
    "T_tip_ideal_delta_n",
    "T_total_ideal_delta_n",
    "T_tip_pretest_fixed_n",
    "T_total_pretest_fixed_n",
    "pretest_fixed_ratio_to_25cm",
    "T_tip_target_fixed_n",
    "T_total_target_fixed_n",
    "target_fixed_ratio_to_25cm",
    "gain_vs_root_pretest_percent",
    "gain_vs_root_target_percent",
    "loss_vs_25cm_pretest_percent",
    "loss_vs_25cm_target_percent",
)


@dataclass(frozen=True)
class DeploymentSweepRow:
    case_id: str
    bias_deg: float
    stiffness_multiplier: float
    moment_scale: float
    theta_final_deg: float
    deployment_progress_final: float
    D_geo_final_m: float
    D_aero_final_m: float
    thrust_root_final_n: float
    thrust_tip_final_n: float
    thrust_total_final_n: float
    tip_aero_effectiveness_final: float
    hinge_state: str
    stable_flag: bool
    reaches_meaningful_deployment_flag: bool
    reaches_open_stop_flag: bool
    open_latch_diagnostic: bool
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

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "case_id": self.case_id,
            "bias_deg": self.bias_deg,
            "stiffness_multiplier": self.stiffness_multiplier,
            "moment_scale": self.moment_scale,
            "theta_final_deg": self.theta_final_deg,
            "deployment_progress_final": self.deployment_progress_final,
            "D_geo_final_m": self.D_geo_final_m,
            "D_aero_final_m": self.D_aero_final_m,
            "thrust_root_final_n": self.thrust_root_final_n,
            "thrust_tip_final_n": self.thrust_tip_final_n,
            "thrust_total_final_n": self.thrust_total_final_n,
            "tip_aero_effectiveness_final": self.tip_aero_effectiveness_final,
            "hinge_state": self.hinge_state,
            "stable_flag": self.stable_flag,
            "reaches_meaningful_deployment_flag": self.reaches_meaningful_deployment_flag,
            "reaches_open_stop_flag": self.reaches_open_stop_flag,
            "open_latch_diagnostic": self.open_latch_diagnostic,
            "T_root_n": self.T_root_n,
            "T_tip_ideal_delta_n": self.T_tip_ideal_delta_n,
            "T_total_ideal_delta_n": self.T_total_ideal_delta_n,
            "T_tip_pretest_fixed_n": self.T_tip_pretest_fixed_n,
            "T_total_pretest_fixed_n": self.T_total_pretest_fixed_n,
            "pretest_fixed_ratio_to_25cm": self.pretest_fixed_ratio_to_25cm,
            "T_tip_target_fixed_n": self.T_tip_target_fixed_n,
            "T_total_target_fixed_n": self.T_total_target_fixed_n,
            "target_fixed_ratio_to_25cm": self.target_fixed_ratio_to_25cm,
            "gain_vs_root_pretest_percent": self.gain_vs_root_pretest_percent,
            "gain_vs_root_target_percent": self.gain_vs_root_target_percent,
            "loss_vs_25cm_pretest_percent": self.loss_vs_25cm_pretest_percent,
            "loss_vs_25cm_target_percent": self.loss_vs_25cm_target_percent,
        }


def _meaningful_deployment(
    progress: float,
    d_aero_m: float,
) -> bool:
    return progress >= MEANINGFUL_DEPLOYMENT_PROGRESS or d_aero_m >= MEANINGFUL_D_AERO_M


def _thrust_evaluation_fields(
    *,
    d_aero_m: float,
    context: FoldableEvaluationContext,
    prop_entry: PropellerEntry,
    constant_rpm: float,
) -> FoldableThrustEvaluation:
    return evaluate_foldable_thrust_at_state(
        d_aero=d_aero_m,
        context=context,
        prop_entry=prop_entry,
        rpm=constant_rpm,
    )


def _run_sweep_case(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    case_id: str,
    bias_deg: float,
    stiffness_multiplier: float,
    moment_scale: float,
    evaluation_context: FoldableEvaluationContext,
    initial_stow_offset_deg: float = 0.0,
    open_latch_diagnostic: bool = False,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> DeploymentSweepRow:
    hinge = base_config.hinge
    new_hinge = replace(
        hinge,
        cent_moment_model="geometric_radial",
        deployment_bias_angle_deg=bias_deg,
        initial_stow_offset_deg=initial_stow_offset_deg,
        hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad * stiffness_multiplier,
        cent_moment_geometry_scale=moment_scale,
        open_latch_diagnostic=open_latch_diagnostic,
    )
    cfg = replace(base_config, hinge=new_hinge)
    sim = PrescribedRpmConfig(
        dt_s=dt_s,
        t_end_s=t_end_s,
        rpm_mode="constant",
        constant_rpm=constant_rpm,
    )
    states = run_prescribed_rpm_physics(cfg, prop_entry, sim=sim)
    metrics = analyze_physics_stability(
        states,
        cfg,
        case_id=case_id,
        rpm_profile=f"constant_{constant_rpm:g}",
        dt_s=dt_s,
    )
    final = states[-1]
    progress = deployment_progress_from_theta(
        final.theta_deg,
        theta_min_deg=hinge.theta_min_deg,
        theta_max_deg=hinge.theta_max_deg,
    )
    tip_eff = geometric_tip_exposure_01(final.theta_deg, cfg)
    thrust_eval = _thrust_evaluation_fields(
        d_aero_m=final.aerodynamic_effective_diameter_m,
        context=evaluation_context,
        prop_entry=prop_entry,
        constant_rpm=constant_rpm,
    )
    return DeploymentSweepRow(
        case_id=case_id,
        bias_deg=bias_deg,
        stiffness_multiplier=stiffness_multiplier,
        moment_scale=moment_scale,
        theta_final_deg=final.theta_deg,
        deployment_progress_final=progress,
        D_geo_final_m=final.geometric_effective_diameter_m,
        D_aero_final_m=final.aerodynamic_effective_diameter_m,
        thrust_root_final_n=final.thrust_root_n,
        thrust_tip_final_n=final.thrust_tip_n,
        thrust_total_final_n=final.thrust_total_n,
        tip_aero_effectiveness_final=tip_eff,
        hinge_state=final.hinge_state,
        stable_flag=metrics.stable_flag,
        reaches_meaningful_deployment_flag=_meaningful_deployment(
            progress, final.aerodynamic_effective_diameter_m
        ),
        reaches_open_stop_flag=final.hinge_state == "open_stop",
        open_latch_diagnostic=open_latch_diagnostic,
        T_root_n=thrust_eval.T_root_n,
        T_tip_ideal_delta_n=thrust_eval.T_tip_ideal_delta_n,
        T_total_ideal_delta_n=thrust_eval.T_total_ideal_delta_n,
        T_tip_pretest_fixed_n=thrust_eval.T_tip_pretest_fixed_n,
        T_total_pretest_fixed_n=thrust_eval.T_total_pretest_fixed_n,
        pretest_fixed_ratio_to_25cm=thrust_eval.pretest_fixed_ratio_to_25cm,
        T_tip_target_fixed_n=thrust_eval.T_tip_target_fixed_n,
        T_total_target_fixed_n=thrust_eval.T_total_target_fixed_n,
        target_fixed_ratio_to_25cm=thrust_eval.target_fixed_ratio_to_25cm,
        gain_vs_root_pretest_percent=thrust_eval.gain_vs_root_pretest_percent,
        gain_vs_root_target_percent=thrust_eval.gain_vs_root_target_percent,
        loss_vs_25cm_pretest_percent=thrust_eval.loss_vs_25cm_pretest_percent,
        loss_vs_25cm_target_percent=thrust_eval.loss_vs_25cm_target_percent,
    )


def run_deployment_bias_stiffness_sweep(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    bias_values: Sequence[float] = (0.0, 5.0, 10.0, 15.0, 20.0, 30.0),
    stiffness_multipliers: Sequence[float] = (1.0, 0.75, 0.5, 0.25),
    moment_scales: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    evaluation_context: FoldableEvaluationContext | None = None,
) -> list[DeploymentSweepRow]:
    eval_context = evaluation_context or resolve_foldable_evaluation_context(
        config,
        prop_entry,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
    )
    rows: list[DeploymentSweepRow] = []
    for bias in bias_values:
        for k_mult in stiffness_multipliers:
            for scale in moment_scales:
                case_id = f"bias{bias:g}_k{k_mult:g}_s{scale:g}"
                rows.append(
                    _run_sweep_case(
                        config,
                        prop_entry,
                        case_id=case_id,
                        bias_deg=bias,
                        stiffness_multiplier=k_mult,
                        moment_scale=scale,
                        evaluation_context=eval_context,
                        dt_s=dt_s,
                        t_end_s=t_end_s,
                        constant_rpm=constant_rpm,
                    )
                )
    return rows


def run_open_latch_diagnostic_cases(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    evaluation_context: FoldableEvaluationContext | None = None,
) -> list[DeploymentSweepRow]:
    """Open-stop/latch diagnostic cases (optional mode, not default physics).

    Includes aggressive free-equilibrium cases and near-open start cases that
    demonstrate latch capture at theta_max when the capture threshold is reached.
    """
    specs: tuple[tuple[str, float, float, float, float, bool], ...] = (
        ("latch_free_bias30_k0.25_s5", 30.0, 0.25, 5.0, 0.0, False),
        ("latch_try_bias30_k0.25_s5", 30.0, 0.25, 5.0, 0.0, True),
        ("latch_near_open_start", 10.0, 0.25, 3.0, 175.0, True),
        ("latch_capture_threshold", 0.0, 1.0, 1.0, 175.0, True),
    )
    eval_context = evaluation_context or resolve_foldable_evaluation_context(
        config,
        prop_entry,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
    )
    rows: list[DeploymentSweepRow] = []
    for case_id, bias, k_mult, scale, offset, latch in specs:
        rows.append(
            _run_sweep_case(
                config,
                prop_entry,
                case_id=case_id,
                bias_deg=bias,
                stiffness_multiplier=k_mult,
                moment_scale=scale,
                evaluation_context=eval_context,
                initial_stow_offset_deg=offset,
                open_latch_diagnostic=latch,
                dt_s=dt_s,
                t_end_s=t_end_s,
                constant_rpm=constant_rpm,
            )
        )
    return rows


def write_deployment_bias_stiffness_sweep_csv(
    path: str,
    rows: Sequence[DeploymentSweepRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DEPLOYMENT_BIAS_STIFFNESS_SWEEP_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
