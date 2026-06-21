"""Motor-coupled foldable V2 performance (PyThrust solver + calibrated thrust)."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from typing import Literal, Sequence

from pythrust.propellers.database import PropellerEntry

from ..integration import solve_pythrust_operating_point
from ..models import FoldablePropellerConfig
from ..variants import make_variant_config, variant_id_from_ratios
from .aero import quasi_steady_aero
from .calibration import TUBITAK_LIFT_REFERENCE_FRACTION, TUBITAK_LIFT_TARGET_FRACTION
from .physics_foldable_design_decision import (
    SelectedCaseSpec,
    _resolve_case_state,
)
from .physics_foldable_performance import (
    FoldableEvaluationContext,
    FoldableThrustEvaluation,
    evaluate_foldable_thrust_at_state,
    resolve_foldable_evaluation_context,
)
from .physics_thrust_split_diagnostic import _run_case_final_state

DEFAULT_TARGET_CHECKPOINT_RPM = 7100.0
RPM_AT_CHECKPOINT_TOLERANCE = 50.0
PRETEST_TARGET_RATIO = TUBITAK_LIFT_REFERENCE_FRACTION
TARGET_85_RATIO = TUBITAK_LIFT_TARGET_FRACTION

DEFAULT_THROTTLE_VALUES: tuple[float, ...] = (
    0.0,
    0.3,
    0.5,
    0.7,
    0.85,
    0.95,
    1.0,
)

MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "case_id",
    "throttle",
    "voltage_v",
    "rpm",
    "omega_rad_s",
    "motor_current_a",
    "battery_power_w",
    "motor_torque_nm",
    "aero_torque_nm",
    "system_efficiency",
    "theta_final_deg",
    "D_aero_m",
    "T_root_n",
    "T_tip_ideal_delta_n",
    "T_total_ideal_delta_n",
    "T_total_pretest_fixed_n",
    "T_total_target_fixed_n",
    "ratio_to_25cm_pretest",
    "ratio_to_25cm_target",
    "gain_vs_root_pretest_percent",
    "loss_vs_25cm_pretest_percent",
    "reaches_7100_rpm_flag",
    "reaches_pretest_target_flag",
    "reaches_target_85_flag",
    "operating_note",
)

MOTOR_COUPLED_7100RPM_CHECKPOINT_V2_COLUMNS: tuple[str, ...] = (
    "case_id",
    "variant_id",
    "throttle_at_or_near_7100",
    "rpm",
    "current_a",
    "power_w",
    "motor_torque_nm",
    "aero_torque_nm",
    "theta_final_deg",
    "D_aero_m",
    "T_pretest_n",
    "T_target_n",
    "ratio25_pretest",
    "ratio25_target",
    "motor_margin_note",
)

CaseVariantBinding = tuple[str, str, tuple[int, int] | None]

MOTOR_COUPLED_EVALUATION_CASES: tuple[CaseVariantBinding, ...] = (
    ("TIP_HINGED_250_V02", "root_only_20cm", None),
    ("TIP_HINGED_250_V02", "fixed_25cm_reference", None),
    ("TIP_HINGED_250_V02", "latch_theta0", None),
    ("TIP_HINGED_250_RT65_35", "bias10_k0.25_s5", (65, 35)),
    ("TIP_HINGED_250_V02", "bias5_k0.25_s5", None),
)

CASE_SPEC_BY_ID: dict[str, SelectedCaseSpec] = {
    "root_only_20cm": ("root_only_20cm", "root_only"),
    "fixed_25cm_reference": ("fixed_25cm_reference", "fixed_reference"),
    "latch_theta0": ("latch_theta0", 0.0, 1.0, 1.0, 175.0, True),
    "bias5_k0.25_s3": ("bias5_k0.25_s3", 5.0, 0.25, 3.0, 0.0, False),
    "bias5_k0.25_s5": ("bias5_k0.25_s5", 5.0, 0.25, 5.0, 0.0, False),
    "bias10_k0.25_s5": ("bias10_k0.25_s5", 10.0, 0.25, 5.0, 0.0, False),
}


@dataclass(frozen=True)
class MotorCoupledPerformanceRow:
    variant_id: str
    case_id: str
    throttle: float
    voltage_v: float
    rpm: float
    omega_rad_s: float
    motor_current_a: float
    battery_power_w: float
    motor_torque_nm: float
    aero_torque_nm: float
    system_efficiency: float
    theta_final_deg: float
    D_aero_m: float
    T_root_n: float
    T_tip_ideal_delta_n: float
    T_total_ideal_delta_n: float
    T_total_pretest_fixed_n: float
    T_total_target_fixed_n: float
    ratio_to_25cm_pretest: float
    ratio_to_25cm_target: float
    gain_vs_root_pretest_percent: float
    loss_vs_25cm_pretest_percent: float
    reaches_7100_rpm_flag: bool
    reaches_pretest_target_flag: bool
    reaches_target_85_flag: bool
    operating_note: str

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "variant_id": self.variant_id,
            "case_id": self.case_id,
            "throttle": self.throttle,
            "voltage_v": self.voltage_v,
            "rpm": self.rpm,
            "omega_rad_s": self.omega_rad_s,
            "motor_current_a": self.motor_current_a,
            "battery_power_w": self.battery_power_w,
            "motor_torque_nm": self.motor_torque_nm,
            "aero_torque_nm": self.aero_torque_nm,
            "system_efficiency": self.system_efficiency,
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "T_root_n": self.T_root_n,
            "T_tip_ideal_delta_n": self.T_tip_ideal_delta_n,
            "T_total_ideal_delta_n": self.T_total_ideal_delta_n,
            "T_total_pretest_fixed_n": self.T_total_pretest_fixed_n,
            "T_total_target_fixed_n": self.T_total_target_fixed_n,
            "ratio_to_25cm_pretest": self.ratio_to_25cm_pretest,
            "ratio_to_25cm_target": self.ratio_to_25cm_target,
            "gain_vs_root_pretest_percent": self.gain_vs_root_pretest_percent,
            "loss_vs_25cm_pretest_percent": self.loss_vs_25cm_pretest_percent,
            "reaches_7100_rpm_flag": self.reaches_7100_rpm_flag,
            "reaches_pretest_target_flag": self.reaches_pretest_target_flag,
            "reaches_target_85_flag": self.reaches_target_85_flag,
            "operating_note": self.operating_note,
        }


@dataclass(frozen=True)
class MotorCoupled7100CheckpointRow:
    case_id: str
    variant_id: str
    throttle_at_or_near_7100: float
    rpm: float
    current_a: float
    power_w: float
    motor_torque_nm: float
    aero_torque_nm: float
    theta_final_deg: float
    D_aero_m: float
    T_pretest_n: float
    T_target_n: float
    ratio25_pretest: float
    ratio25_target: float
    motor_margin_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "throttle_at_or_near_7100": self.throttle_at_or_near_7100,
            "rpm": self.rpm,
            "current_a": self.current_a,
            "power_w": self.power_w,
            "motor_torque_nm": self.motor_torque_nm,
            "aero_torque_nm": self.aero_torque_nm,
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "T_pretest_n": self.T_pretest_n,
            "T_target_n": self.T_target_n,
            "ratio25_pretest": self.ratio25_pretest,
            "ratio25_target": self.ratio25_target,
            "motor_margin_note": self.motor_margin_note,
        }


def resolve_variant_config(
    base_config: FoldablePropellerConfig,
    variant_id: str,
    root_tip_ratio: tuple[int, int] | None,
) -> FoldablePropellerConfig:
    if root_tip_ratio is None:
        if base_config.id != variant_id:
            raise ValueError(
                f"Base config id {base_config.id!r} does not match variant {variant_id!r}"
            )
        return base_config
    root_ratio, tip_ratio = root_tip_ratio
    expected = variant_id_from_ratios(root_ratio, tip_ratio)
    if expected != variant_id:
        raise ValueError(
            f"Variant id {variant_id!r} does not match ratios RT{root_ratio}_{tip_ratio}"
        )
    return make_variant_config(base_config, root_ratio, tip_ratio)


def apply_calibration_settings(
    config: FoldablePropellerConfig,
    *,
    thrust_split_mode: str = "calibrated_effective_diameter_delta",
    calibration_preset: str = "pretest_70_percent_fixed",
) -> FoldablePropellerConfig:
    return replace(
        config,
        calibration=replace(
            config.calibration,
            thrust_split_mode=thrust_split_mode,
            tip_delta_calibration_preset=calibration_preset,
        ),
    )


def _reference_thrust_evaluation(
    thrust: FoldableThrustEvaluation,
    context: FoldableEvaluationContext,
) -> FoldableThrustEvaluation:
    reference_total = context.reference_total_25cm_n
    root = thrust.T_root_n
    baseline = context.T_root_baseline_n
    gain = (
        100.0 * (reference_total - baseline) / baseline if baseline > 0.0 else 0.0
    )
    return FoldableThrustEvaluation(
        T_root_n=root,
        T_tip_ideal_delta_n=reference_total - root,
        T_total_ideal_delta_n=reference_total,
        T_tip_pretest_fixed_n=reference_total - root,
        T_total_pretest_fixed_n=reference_total,
        pretest_fixed_ratio_to_25cm=1.0,
        T_tip_target_fixed_n=reference_total - root,
        T_total_target_fixed_n=reference_total,
        target_fixed_ratio_to_25cm=1.0,
        gain_vs_root_pretest_percent=gain,
        gain_vs_root_target_percent=gain,
        loss_vs_25cm_pretest_percent=0.0,
        loss_vs_25cm_target_percent=0.0,
    )


def _tip_effectiveness_from_theta(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    case_id: str,
    *,
    dt_s: float,
    t_end_s: float,
    constant_rpm: float,
) -> float:
    spec = CASE_SPEC_BY_ID.get(case_id)
    if spec is None or len(spec) == 2:
        return 1.0 if case_id == "fixed_25cm_reference" else 0.0
    _, bias, k_mult, scale, offset, latch = spec  # type: ignore[misc]
    _theta, tip_eff = _run_case_final_state(
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
    return tip_eff


def evaluate_motor_coupled_case_at_throttle(
    *,
    variant_id: str,
    case_id: str,
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    eval_context: FoldableEvaluationContext,
    theta_final_deg: float,
    d_aero_m: float,
    throttle: float,
    target_checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    rho: float = 1.225,
    tip_aero_effectiveness: float = 1.0,
) -> MotorCoupledPerformanceRow:
    """One motor-coupled operating row at fixed deployment geometry."""
    v_applied = throttle * config.battery.voltage_v
    if throttle <= 0.0:
        return MotorCoupledPerformanceRow(
            variant_id=variant_id,
            case_id=case_id,
            throttle=throttle,
            voltage_v=v_applied,
            rpm=0.0,
            omega_rad_s=0.0,
            motor_current_a=0.0,
            battery_power_w=0.0,
            motor_torque_nm=0.0,
            aero_torque_nm=0.0,
            system_efficiency=0.0,
            theta_final_deg=theta_final_deg,
            D_aero_m=d_aero_m,
            T_root_n=0.0,
            T_tip_ideal_delta_n=0.0,
            T_total_ideal_delta_n=0.0,
            T_total_pretest_fixed_n=0.0,
            T_total_target_fixed_n=0.0,
            ratio_to_25cm_pretest=0.0,
            ratio_to_25cm_target=0.0,
            gain_vs_root_pretest_percent=0.0,
            loss_vs_25cm_pretest_percent=100.0,
            reaches_7100_rpm_flag=False,
            reaches_pretest_target_flag=False,
            reaches_target_85_flag=False,
            operating_note="Zero throttle; motor idle",
        )

    operating_point = solve_pythrust_operating_point(
        config, prop_entry, throttle, rho=rho
    )
    rpm = max(0.0, operating_point.rpm)
    omega = rpm * math.pi / 30.0
    eff = max(0.0, min(1.0, tip_aero_effectiveness))
    _, aero_torque_nm, _ = quasi_steady_aero(
        omega,
        d_aero_m,
        prop_entry,
        rho=rho,
        aero_effectiveness=eff,
    )

    thrust = evaluate_foldable_thrust_at_state(
        d_aero=d_aero_m,
        context=eval_context,
        prop_entry=prop_entry,
        rpm=rpm,
        rho=rho,
    )
    if case_id == "fixed_25cm_reference":
        thrust = _reference_thrust_evaluation(thrust, eval_context)

    reaches_7100 = rpm >= target_checkpoint_rpm - RPM_AT_CHECKPOINT_TOLERANCE
    note_parts = [
        f"PyThrust equilibrium @ {prop_entry.diameter_m:.3f} m reference load",
    ]
    if not operating_point.is_feasible:
        note_parts.append(f"infeasible: {operating_point.infeasible_reason}")
    if not reaches_7100 and throttle >= 0.99:
        note_parts.append(
            f"full throttle RPM {rpm:.0f} below {target_checkpoint_rpm:.0f} checkpoint"
        )
    if aero_torque_nm > operating_point.torque_nm * 1.05 and rpm > 0.0:
        note_parts.append(
            "foldable D_aero load exceeds solver reference torque at this RPM"
        )

    return MotorCoupledPerformanceRow(
        variant_id=variant_id,
        case_id=case_id,
        throttle=throttle,
        voltage_v=operating_point.motor_voltage_v,
        rpm=rpm,
        omega_rad_s=omega,
        motor_current_a=max(0.0, operating_point.motor_current_a),
        battery_power_w=max(0.0, operating_point.battery_power_w),
        motor_torque_nm=operating_point.torque_nm,
        aero_torque_nm=aero_torque_nm,
        system_efficiency=max(0.0, operating_point.system_efficiency),
        theta_final_deg=theta_final_deg,
        D_aero_m=d_aero_m,
        T_root_n=thrust.T_root_n,
        T_tip_ideal_delta_n=thrust.T_tip_ideal_delta_n,
        T_total_ideal_delta_n=thrust.T_total_ideal_delta_n,
        T_total_pretest_fixed_n=thrust.T_total_pretest_fixed_n,
        T_total_target_fixed_n=thrust.T_total_target_fixed_n,
        ratio_to_25cm_pretest=thrust.pretest_fixed_ratio_to_25cm,
        ratio_to_25cm_target=thrust.target_fixed_ratio_to_25cm,
        gain_vs_root_pretest_percent=thrust.gain_vs_root_pretest_percent,
        loss_vs_25cm_pretest_percent=thrust.loss_vs_25cm_pretest_percent,
        reaches_7100_rpm_flag=reaches_7100,
        reaches_pretest_target_flag=(
            thrust.pretest_fixed_ratio_to_25cm >= PRETEST_TARGET_RATIO - 0.005
        ),
        reaches_target_85_flag=(
            thrust.target_fixed_ratio_to_25cm >= TARGET_85_RATIO - 0.005
        ),
        operating_note="; ".join(note_parts),
    )


def run_motor_coupled_foldable_performance_v2(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    evaluation_cases: Sequence[CaseVariantBinding] = MOTOR_COUPLED_EVALUATION_CASES,
    throttle_values: Sequence[float] = DEFAULT_THROTTLE_VALUES,
    thrust_split_mode: str = "calibrated_effective_diameter_delta",
    calibration_preset: str = "pretest_70_percent_fixed",
    target_checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    rho: float = 1.225,
) -> list[MotorCoupledPerformanceRow]:
    """Sweep throttle for selected variant/case bindings with calibrated thrust."""
    rows: list[MotorCoupledPerformanceRow] = []

    for variant_id, case_id, ratio in evaluation_cases:
        config = apply_calibration_settings(
            resolve_variant_config(base_config, variant_id, ratio),
            thrust_split_mode=thrust_split_mode,
            calibration_preset=calibration_preset,
        )
        eval_context = resolve_foldable_evaluation_context(
            config,
            prop_entry,
            dt_s=dt_s,
            t_end_s=t_end_s,
            constant_rpm=constant_rpm,
            rho=rho,
        )
        spec = CASE_SPEC_BY_ID[case_id]
        _case, theta, d_aero, _latch, _ctx = _resolve_case_state(
            config=config,
            prop_entry=prop_entry,
            spec=spec,
            d_root=eval_context.d_root_m,
            d_open=eval_context.d_open_m,
            context=eval_context,
            constant_rpm=constant_rpm,
            dt_s=dt_s,
            t_end_s=t_end_s,
            rho=rho,
        )
        tip_eff = _tip_effectiveness_from_theta(
            config,
            prop_entry,
            case_id,
            dt_s=dt_s,
            t_end_s=t_end_s,
            constant_rpm=constant_rpm,
        )

        for throttle in throttle_values:
            rows.append(
                evaluate_motor_coupled_case_at_throttle(
                    variant_id=variant_id,
                    case_id=case_id,
                    config=config,
                    prop_entry=prop_entry,
                    eval_context=eval_context,
                    theta_final_deg=theta,
                    d_aero_m=d_aero,
                    throttle=throttle,
                    target_checkpoint_rpm=target_checkpoint_rpm,
                    rho=rho,
                    tip_aero_effectiveness=tip_eff,
                )
            )
    return rows


def run_motor_coupled_7100rpm_checkpoint_v2(
    performance_rows: Sequence[MotorCoupledPerformanceRow],
    *,
    target_checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
) -> list[MotorCoupled7100CheckpointRow]:
    """Pick throttle nearest 7100 rpm per case, or report motor limit clearly."""
    checkpoints: list[MotorCoupled7100CheckpointRow] = []
    keys = {(row.variant_id, row.case_id) for row in performance_rows}

    for variant_id, case_id in sorted(keys):
        case_rows = [
            row
            for row in performance_rows
            if row.variant_id == variant_id and row.case_id == case_id
        ]
        positive = [row for row in case_rows if row.throttle > 0.0]
        if not positive:
            continue

        selected = min(
            positive,
            key=lambda row: abs(row.rpm - target_checkpoint_rpm),
        )
        max_rpm_row = max(positive, key=lambda row: row.rpm)

        if selected.rpm >= target_checkpoint_rpm - RPM_AT_CHECKPOINT_TOLERANCE:
            margin_note = (
                f"At or above checkpoint: {selected.rpm:.0f} rpm "
                f"at throttle={selected.throttle:.2f}"
            )
        elif max_rpm_row.rpm < target_checkpoint_rpm - RPM_AT_CHECKPOINT_TOLERANCE:
            margin_note = (
                f"Motor cannot reach {target_checkpoint_rpm:.0f} rpm; "
                f"max {max_rpm_row.rpm:.0f} rpm at throttle={max_rpm_row.throttle:.2f}"
            )
        else:
            margin_note = (
                f"Nearest to checkpoint: {selected.rpm:.0f} rpm "
                f"at throttle={selected.throttle:.2f}; "
                f"full throttle {max_rpm_row.rpm:.0f} rpm exceeds checkpoint"
            )

        checkpoints.append(
            MotorCoupled7100CheckpointRow(
                case_id=case_id,
                variant_id=variant_id,
                throttle_at_or_near_7100=selected.throttle,
                rpm=selected.rpm,
                current_a=selected.motor_current_a,
                power_w=selected.battery_power_w,
                motor_torque_nm=selected.motor_torque_nm,
                aero_torque_nm=selected.aero_torque_nm,
                theta_final_deg=selected.theta_final_deg,
                D_aero_m=selected.D_aero_m,
                T_pretest_n=selected.T_total_pretest_fixed_n,
                T_target_n=selected.T_total_target_fixed_n,
                ratio25_pretest=selected.ratio_to_25cm_pretest,
                ratio25_target=selected.ratio_to_25cm_target,
                motor_margin_note=margin_note,
            )
        )
    return checkpoints


def write_motor_coupled_foldable_performance_v2_csv(
    path: str,
    rows: Sequence[MotorCoupledPerformanceRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_motor_coupled_7100rpm_checkpoint_v2_csv(
    path: str,
    rows: Sequence[MotorCoupled7100CheckpointRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(MOTOR_COUPLED_7100RPM_CHECKPOINT_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
