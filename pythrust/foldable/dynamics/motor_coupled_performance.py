"""Motor-coupled foldable V2 performance (PyThrust solver + calibrated thrust)."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from typing import Literal, Sequence

AeroTorqueBasis = Literal[
    "pythrust_solver_reference",
    "foldable_proxy",
    "not_computed",
]
MotorCouplingLevel = Literal[
    "reference_load_postprocess",
    "foldable_load_proxy",
    "fully_coupled_solver",
]

MOTOR_COUPLING_LEVEL: MotorCouplingLevel = "reference_load_postprocess"
SOLVER_LOAD_NOTE = (
    "RPM/current/power are from PyThrust reference propeller equilibrium; "
    "foldable D_aero load is post-processed and not yet fed back into solver."
)

from pythrust.propellers.database import PropellerEntry

from ..integration import solve_pythrust_operating_point
from ..models import FoldablePropellerConfig
from ..variants import make_variant_config, variant_id_from_ratios
from .aero import quasi_steady_aero
from .calibration import PRETEST_REFERENCE_FRACTION, PROJECT_TARGET_FRACTION
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
PRETEST_TARGET_RATIO = PRETEST_REFERENCE_FRACTION
TARGET_85_RATIO = PROJECT_TARGET_FRACTION

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
    "reference_25cm_at_checkpoint_7100_n",
    "reference_25cm_at_current_rpm_n",
    "ratio_to_checkpoint_25cm_pretest",
    "ratio_to_current_25cm_pretest",
    "reference_basis_note",
    "aero_torque_basis",
    "compact_root_20cm_thrust_n",
    "variant_root_segment_thrust_n",
    "gain_vs_compact_root_20cm_percent",
    "gain_vs_variant_root_segment_percent",
    "root_baseline_note",
    "motor_torque_margin_nm",
    "motor_torque_margin_percent",
    "torque_margin_note",
    "motor_coupling_level",
    "solver_load_note",
)

MOTOR_COUPLED_7100RPM_INTERPOLATED_V2_COLUMNS: tuple[str, ...] = (
    "case_id",
    "variant_id",
    "target_rpm",
    "interpolated_throttle",
    "rpm",
    "current_a",
    "power_w",
    "motor_torque_nm",
    "aero_torque_nm",
    "theta_final_deg",
    "D_aero_m",
    "T_root_n",
    "T_total_pretest_fixed_n",
    "T_total_target_fixed_n",
    "reference_25cm_at_checkpoint_7100_n",
    "reference_25cm_at_current_rpm_n",
    "ratio_to_checkpoint_25cm_pretest",
    "ratio_to_current_25cm_pretest",
    "gain_vs_root_current_rpm_percent",
    "motor_margin_note",
    "interpolation_note",
    "aero_torque_basis",
    "compact_root_20cm_thrust_n",
    "variant_root_segment_thrust_n",
    "gain_vs_compact_root_20cm_percent",
    "gain_vs_variant_root_segment_percent",
    "root_baseline_note",
    "motor_torque_margin_nm",
    "motor_torque_margin_percent",
    "torque_margin_note",
    "motor_coupling_level",
    "solver_load_note",
)

MOTOR_COUPLED_CONSISTENCY_AUDIT_V2_COLUMNS: tuple[str, ...] = (
    "check_id",
    "status",
    "value",
    "expected_behavior",
    "note",
)

MOTOR_COUPLED_REFERENCE_CONSISTENCY_V2_COLUMNS: tuple[str, ...] = (
    "row_type",
    "rpm",
    "thrust_n",
    "reference_basis",
    "interpretation_note",
    "motor_coupling_level",
    "solver_load_note",
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
    "aero_torque_basis",
    "motor_coupling_level",
    "solver_load_note",
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
    aero_torque_nm: float | None
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
    reference_25cm_at_checkpoint_7100_n: float
    reference_25cm_at_current_rpm_n: float
    ratio_to_checkpoint_25cm_pretest: float
    ratio_to_current_25cm_pretest: float
    reference_basis_note: str
    aero_torque_basis: AeroTorqueBasis
    compact_root_20cm_thrust_n: float
    variant_root_segment_thrust_n: float
    gain_vs_compact_root_20cm_percent: float
    gain_vs_variant_root_segment_percent: float
    root_baseline_note: str
    motor_torque_margin_nm: float | None
    motor_torque_margin_percent: float | None
    torque_margin_note: str
    motor_coupling_level: MotorCouplingLevel
    solver_load_note: str

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
            "aero_torque_nm": _csv_aero_torque(self.aero_torque_nm, self.aero_torque_basis),
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
            "reference_25cm_at_checkpoint_7100_n": (
                self.reference_25cm_at_checkpoint_7100_n
            ),
            "reference_25cm_at_current_rpm_n": self.reference_25cm_at_current_rpm_n,
            "ratio_to_checkpoint_25cm_pretest": self.ratio_to_checkpoint_25cm_pretest,
            "ratio_to_current_25cm_pretest": self.ratio_to_current_25cm_pretest,
            "reference_basis_note": self.reference_basis_note,
            "aero_torque_basis": self.aero_torque_basis,
            "compact_root_20cm_thrust_n": self.compact_root_20cm_thrust_n,
            "variant_root_segment_thrust_n": self.variant_root_segment_thrust_n,
            "gain_vs_compact_root_20cm_percent": self.gain_vs_compact_root_20cm_percent,
            "gain_vs_variant_root_segment_percent": (
                self.gain_vs_variant_root_segment_percent
            ),
            "root_baseline_note": self.root_baseline_note,
            "motor_torque_margin_nm": _csv_optional_float(self.motor_torque_margin_nm),
            "motor_torque_margin_percent": _csv_optional_float(
                self.motor_torque_margin_percent
            ),
            "torque_margin_note": self.torque_margin_note,
            "motor_coupling_level": self.motor_coupling_level,
            "solver_load_note": self.solver_load_note,
        }


@dataclass(frozen=True)
class AeroTorqueEvaluation:
    aero_torque_nm: float | None
    basis: AeroTorqueBasis


@dataclass(frozen=True)
class RootBaselineEvaluation:
    compact_root_20cm_thrust_n: float
    variant_root_segment_thrust_n: float
    gain_vs_compact_root_20cm_percent: float
    gain_vs_variant_root_segment_percent: float
    root_baseline_note: str


@dataclass(frozen=True)
class TorqueMarginEvaluation:
    motor_torque_margin_nm: float | None
    motor_torque_margin_percent: float | None
    torque_margin_note: str


@dataclass(frozen=True)
class InterpolatedMotorScalars:
    target_rpm: float
    interpolated_throttle: float
    rpm: float
    motor_current_a: float
    battery_power_w: float
    motor_torque_nm: float
    aero_torque_nm: float | None
    system_efficiency: float
    interpolation_note: str


@dataclass(frozen=True)
class MotorCoupled7100InterpolatedRow:
    case_id: str
    variant_id: str
    target_rpm: float
    interpolated_throttle: float
    rpm: float
    current_a: float
    power_w: float
    motor_torque_nm: float
    aero_torque_nm: float | None
    theta_final_deg: float
    D_aero_m: float
    T_root_n: float
    T_total_pretest_fixed_n: float
    T_total_target_fixed_n: float
    reference_25cm_at_checkpoint_7100_n: float
    reference_25cm_at_current_rpm_n: float
    ratio_to_checkpoint_25cm_pretest: float
    ratio_to_current_25cm_pretest: float
    gain_vs_root_current_rpm_percent: float
    motor_margin_note: str
    interpolation_note: str
    aero_torque_basis: AeroTorqueBasis
    compact_root_20cm_thrust_n: float
    variant_root_segment_thrust_n: float
    gain_vs_compact_root_20cm_percent: float
    gain_vs_variant_root_segment_percent: float
    root_baseline_note: str
    motor_torque_margin_nm: float | None
    motor_torque_margin_percent: float | None
    torque_margin_note: str
    motor_coupling_level: MotorCouplingLevel
    solver_load_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "target_rpm": self.target_rpm,
            "interpolated_throttle": self.interpolated_throttle,
            "rpm": self.rpm,
            "current_a": self.current_a,
            "power_w": self.power_w,
            "motor_torque_nm": self.motor_torque_nm,
            "aero_torque_nm": _csv_aero_torque(self.aero_torque_nm, self.aero_torque_basis),
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "T_root_n": self.T_root_n,
            "T_total_pretest_fixed_n": self.T_total_pretest_fixed_n,
            "T_total_target_fixed_n": self.T_total_target_fixed_n,
            "reference_25cm_at_checkpoint_7100_n": (
                self.reference_25cm_at_checkpoint_7100_n
            ),
            "reference_25cm_at_current_rpm_n": self.reference_25cm_at_current_rpm_n,
            "ratio_to_checkpoint_25cm_pretest": self.ratio_to_checkpoint_25cm_pretest,
            "ratio_to_current_25cm_pretest": self.ratio_to_current_25cm_pretest,
            "gain_vs_root_current_rpm_percent": self.gain_vs_root_current_rpm_percent,
            "motor_margin_note": self.motor_margin_note,
            "interpolation_note": self.interpolation_note,
            "aero_torque_basis": self.aero_torque_basis,
            "compact_root_20cm_thrust_n": self.compact_root_20cm_thrust_n,
            "variant_root_segment_thrust_n": self.variant_root_segment_thrust_n,
            "gain_vs_compact_root_20cm_percent": self.gain_vs_compact_root_20cm_percent,
            "gain_vs_variant_root_segment_percent": (
                self.gain_vs_variant_root_segment_percent
            ),
            "root_baseline_note": self.root_baseline_note,
            "motor_torque_margin_nm": _csv_optional_float(self.motor_torque_margin_nm),
            "motor_torque_margin_percent": _csv_optional_float(
                self.motor_torque_margin_percent
            ),
            "torque_margin_note": self.torque_margin_note,
            "motor_coupling_level": self.motor_coupling_level,
            "solver_load_note": self.solver_load_note,
        }


@dataclass(frozen=True)
class MotorCoupledReferenceConsistencyRow:
    row_type: str
    rpm: float
    thrust_n: float
    reference_basis: str
    interpretation_note: str
    motor_coupling_level: MotorCouplingLevel
    solver_load_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "row_type": self.row_type,
            "rpm": self.rpm,
            "thrust_n": self.thrust_n,
            "reference_basis": self.reference_basis,
            "interpretation_note": self.interpretation_note,
            "motor_coupling_level": self.motor_coupling_level,
            "solver_load_note": self.solver_load_note,
        }


@dataclass(frozen=True)
class MotorCoupledConsistencyAuditRow:
    check_id: str
    status: str
    value: str
    expected_behavior: str
    note: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "value": self.value,
            "expected_behavior": self.expected_behavior,
            "note": self.note,
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
    aero_torque_nm: float | None
    theta_final_deg: float
    D_aero_m: float
    T_pretest_n: float
    T_target_n: float
    ratio25_pretest: float
    ratio25_target: float
    motor_margin_note: str
    aero_torque_basis: AeroTorqueBasis
    motor_coupling_level: MotorCouplingLevel
    solver_load_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "throttle_at_or_near_7100": self.throttle_at_or_near_7100,
            "rpm": self.rpm,
            "current_a": self.current_a,
            "power_w": self.power_w,
            "motor_torque_nm": self.motor_torque_nm,
            "aero_torque_nm": _csv_aero_torque(self.aero_torque_nm, self.aero_torque_basis),
            "theta_final_deg": self.theta_final_deg,
            "D_aero_m": self.D_aero_m,
            "T_pretest_n": self.T_pretest_n,
            "T_target_n": self.T_target_n,
            "ratio25_pretest": self.ratio25_pretest,
            "ratio25_target": self.ratio25_target,
            "motor_margin_note": self.motor_margin_note,
            "aero_torque_basis": self.aero_torque_basis,
            "motor_coupling_level": self.motor_coupling_level,
            "solver_load_note": self.solver_load_note,
        }


def _csv_optional_float(value: float | None) -> str | float:
    if value is None:
        return ""
    return value


def _csv_aero_torque(value: float | None, basis: AeroTorqueBasis) -> str | float:
    if basis == "not_computed" or value is None:
        return ""
    return value


def _percent_gain(value: float, baseline: float) -> float:
    if baseline <= 0.0:
        return 0.0
    return 100.0 * (value - baseline) / baseline


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


def reference_25cm_at_rpm_n(
    checkpoint_reference_n: float,
    rpm: float,
    *,
    checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
) -> float:
    """Estimate 25 cm reference thrust at rpm via n² scaling (proxy, not measured)."""
    if checkpoint_rpm <= 0.0:
        return 0.0
    return checkpoint_reference_n * (rpm / checkpoint_rpm) ** 2


def _ratio_to_reference(thrust_n: float, reference_n: float) -> float:
    if reference_n <= 0.0:
        return 0.0
    return thrust_n / reference_n


def _reference_basis_note(
    *,
    case_id: str,
    rpm: float,
    checkpoint_rpm: float,
) -> str:
    if case_id == "fixed_25cm_reference":
        return (
            "fixed_25cm_reference row uses engineering checkpoint thrust at 7100 rpm; "
            "current-rpm column is n² proxy for same-diameter comparison only"
        )
    if abs(rpm - checkpoint_rpm) < RPM_AT_CHECKPOINT_TOLERANCE:
        return (
            "operating rpm near checkpoint; checkpoint and current-rpm references "
            "nearly equal"
        )
    return (
        "reference_25cm_at_current_rpm_n is n²-scaled proxy from checkpoint; "
        "not experimental data"
    )


def _aero_effectiveness_for_torque(
    case_id: str,
    tip_aero_effectiveness: float,
) -> float:
    if case_id in ("root_only_20cm", "fixed_25cm_reference"):
        return 1.0
    return max(0.0, min(1.0, tip_aero_effectiveness))


def compute_foldable_aero_torque(
    *,
    omega_rad_s: float,
    d_aero_m: float,
    prop_entry: PropellerEntry,
    case_id: str,
    tip_aero_effectiveness: float,
    rho: float = 1.225,
) -> AeroTorqueEvaluation:
    """Post-processed foldable aero torque at D_aero (not solver equilibrium load)."""
    if omega_rad_s <= 0.0 or d_aero_m <= 0.0:
        return AeroTorqueEvaluation(aero_torque_nm=None, basis="not_computed")
    effectiveness = _aero_effectiveness_for_torque(case_id, tip_aero_effectiveness)
    _thrust, torque_nm, _power = quasi_steady_aero(
        omega_rad_s,
        d_aero_m,
        prop_entry,
        rho=rho,
        aero_effectiveness=effectiveness,
    )
    return AeroTorqueEvaluation(aero_torque_nm=torque_nm, basis="foldable_proxy")


def compute_torque_margin(
    motor_torque_nm: float,
    aero: AeroTorqueEvaluation,
) -> TorqueMarginEvaluation:
    if aero.basis == "not_computed" or aero.aero_torque_nm is None:
        return TorqueMarginEvaluation(
            motor_torque_margin_nm=None,
            motor_torque_margin_percent=None,
            torque_margin_note="not_computed",
        )
    margin_nm = motor_torque_nm - aero.aero_torque_nm
    if motor_torque_nm > 0.0:
        margin_percent = 100.0 * margin_nm / motor_torque_nm
        note = (
            f"margin={margin_nm:.4f} Nm ({margin_percent:.1f}% of motor torque)"
        )
    else:
        margin_percent = None
        note = "motor torque zero; margin undefined"
    return TorqueMarginEvaluation(
        motor_torque_margin_nm=margin_nm,
        motor_torque_margin_percent=margin_percent,
        torque_margin_note=note,
    )


def resolve_root_baselines(
    *,
    t_total_pretest: float,
    rpm: float,
    eval_context: FoldableEvaluationContext,
    compact_eval_context: FoldableEvaluationContext,
    prop_entry: PropellerEntry,
    rho: float = 1.225,
) -> RootBaselineEvaluation:
    compact_root = evaluate_foldable_thrust_at_state(
        d_aero=compact_eval_context.d_root_m,
        context=compact_eval_context,
        prop_entry=prop_entry,
        rpm=rpm,
        rho=rho,
    ).T_total_pretest_fixed_n
    variant_root = evaluate_foldable_thrust_at_state(
        d_aero=eval_context.d_root_m,
        context=eval_context,
        prop_entry=prop_entry,
        rpm=rpm,
        rho=rho,
    ).T_total_pretest_fixed_n
    gain_compact = _percent_gain(t_total_pretest, compact_root)
    gain_variant = _percent_gain(t_total_pretest, variant_root)
    if abs(compact_eval_context.d_root_m - eval_context.d_root_m) < 1e-6:
        note = (
            "compact_root_20cm is compact root baseline; variant_root_segment matches "
            "compact for V02 geometry"
        )
    else:
        note = (
            "compact_root_20cm is compact root baseline; variant_root_segment is "
            "internal geometry diagnostic only"
        )
    return RootBaselineEvaluation(
        compact_root_20cm_thrust_n=compact_root,
        variant_root_segment_thrust_n=variant_root,
        gain_vs_compact_root_20cm_percent=gain_compact,
        gain_vs_variant_root_segment_percent=gain_variant,
        root_baseline_note=note,
    )


def _linear_interpolate(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if abs(x1 - x0) < 1e-12:
        return y0
    fraction = (x - x0) / (x1 - x0)
    return y0 + fraction * (y1 - y0)


def interpolate_motor_scalars_at_target_rpm(
    positive_rows: Sequence[MotorCoupledPerformanceRow],
    target_rpm: float,
) -> InterpolatedMotorScalars:
    """Linearly interpolate motor scalars in rpm from a throttle sweep."""
    if not positive_rows:
        return InterpolatedMotorScalars(
            target_rpm=target_rpm,
            interpolated_throttle=0.0,
            rpm=target_rpm,
            motor_current_a=0.0,
            battery_power_w=0.0,
            motor_torque_nm=0.0,
            aero_torque_nm=0.0,
            system_efficiency=0.0,
            interpolation_note="No positive-throttle sweep rows available",
        )

    ordered = sorted(positive_rows, key=lambda row: row.rpm)
    min_rpm = ordered[0].rpm
    max_rpm = ordered[-1].rpm

    if target_rpm < min_rpm - 1e-6 or target_rpm > max_rpm + 1e-6:
        nearest = min(ordered, key=lambda row: abs(row.rpm - target_rpm))
        direction = "below" if target_rpm < min_rpm else "above"
        return InterpolatedMotorScalars(
            target_rpm=target_rpm,
            interpolated_throttle=nearest.throttle,
            rpm=nearest.rpm,
            motor_current_a=nearest.motor_current_a,
            battery_power_w=nearest.battery_power_w,
            motor_torque_nm=nearest.motor_torque_nm,
            aero_torque_nm=nearest.aero_torque_nm,
            system_efficiency=nearest.system_efficiency,
            interpolation_note=(
                f"TARGET OUTSIDE SWEEP: {target_rpm:.0f} rpm is {direction} "
                f"[{min_rpm:.0f}, {max_rpm:.0f}]; using nearest throttle "
                f"{nearest.throttle:.2f} @ {nearest.rpm:.0f} rpm"
            ),
        )

    if abs(target_rpm - ordered[0].rpm) < 1e-6:
        row = ordered[0]
        return InterpolatedMotorScalars(
            target_rpm=target_rpm,
            interpolated_throttle=row.throttle,
            rpm=target_rpm,
            motor_current_a=row.motor_current_a,
            battery_power_w=row.battery_power_w,
            motor_torque_nm=row.motor_torque_nm,
            aero_torque_nm=row.aero_torque_nm,
            system_efficiency=row.system_efficiency,
            interpolation_note=(
                f"Exact match at sweep endpoint throttle={row.throttle:.2f}"
            ),
        )
    if abs(target_rpm - ordered[-1].rpm) < 1e-6:
        row = ordered[-1]
        return InterpolatedMotorScalars(
            target_rpm=target_rpm,
            interpolated_throttle=row.throttle,
            rpm=target_rpm,
            motor_current_a=row.motor_current_a,
            battery_power_w=row.battery_power_w,
            motor_torque_nm=row.motor_torque_nm,
            aero_torque_nm=row.aero_torque_nm,
            system_efficiency=row.system_efficiency,
            interpolation_note=(
                f"Exact match at sweep endpoint throttle={row.throttle:.2f}"
            ),
        )

    lower = ordered[0]
    upper = ordered[-1]
    for idx in range(len(ordered) - 1):
        if ordered[idx].rpm <= target_rpm <= ordered[idx + 1].rpm:
            lower = ordered[idx]
            upper = ordered[idx + 1]
            break

    def interp(field: str) -> float:
        return _linear_interpolate(
            target_rpm,
            lower.rpm,
            upper.rpm,
            getattr(lower, field),
            getattr(upper, field),
        )

    throttle = _linear_interpolate(
        target_rpm,
        lower.rpm,
        upper.rpm,
        lower.throttle,
        upper.throttle,
    )
    return InterpolatedMotorScalars(
        target_rpm=target_rpm,
        interpolated_throttle=throttle,
        rpm=target_rpm,
        motor_current_a=interp("motor_current_a"),
        battery_power_w=interp("battery_power_w"),
        motor_torque_nm=interp("motor_torque_nm"),
        aero_torque_nm=interp("aero_torque_nm"),
        system_efficiency=interp("system_efficiency"),
        interpolation_note=(
            f"Linear interpolation between throttle {lower.throttle:.2f} "
            f"({lower.rpm:.0f} rpm) and {upper.throttle:.2f} ({upper.rpm:.0f} rpm)"
        ),
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
    compact_eval_context: FoldableEvaluationContext,
    theta_final_deg: float,
    d_aero_m: float,
    throttle: float,
    target_checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    rho: float = 1.225,
    tip_aero_effectiveness: float = 1.0,
) -> MotorCoupledPerformanceRow:
    """One motor-coupled operating row at fixed deployment geometry."""
    checkpoint_ref_n = eval_context.reference_total_25cm_n
    v_applied = throttle * config.battery.voltage_v

    def _reference_fields(
        rpm: float,
        t_pretest: float,
        *,
        case: str,
    ) -> tuple[float, float, float, float, str]:
        current_ref_n = reference_25cm_at_rpm_n(
            checkpoint_ref_n,
            rpm,
            checkpoint_rpm=target_checkpoint_rpm,
        )
        return (
            checkpoint_ref_n,
            current_ref_n,
            _ratio_to_reference(t_pretest, checkpoint_ref_n),
            _ratio_to_reference(t_pretest, current_ref_n),
            _reference_basis_note(
                case_id=case,
                rpm=rpm,
                checkpoint_rpm=target_checkpoint_rpm,
            ),
        )

    if throttle <= 0.0:
        (
            checkpoint_ref,
            current_ref,
            ratio_checkpoint,
            ratio_current,
            basis_note,
        ) = _reference_fields(0.0, 0.0, case=case_id)
        idle_aero = AeroTorqueEvaluation(aero_torque_nm=None, basis="not_computed")
        idle_margin = compute_torque_margin(0.0, idle_aero)
        idle_baselines = resolve_root_baselines(
            t_total_pretest=0.0,
            rpm=0.0,
            eval_context=eval_context,
            compact_eval_context=compact_eval_context,
            prop_entry=prop_entry,
            rho=rho,
        )
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
            aero_torque_nm=None,
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
            reference_25cm_at_checkpoint_7100_n=checkpoint_ref,
            reference_25cm_at_current_rpm_n=current_ref,
            ratio_to_checkpoint_25cm_pretest=ratio_checkpoint,
            ratio_to_current_25cm_pretest=ratio_current,
            reference_basis_note=basis_note,
            aero_torque_basis=idle_aero.basis,
            compact_root_20cm_thrust_n=idle_baselines.compact_root_20cm_thrust_n,
            variant_root_segment_thrust_n=idle_baselines.variant_root_segment_thrust_n,
            gain_vs_compact_root_20cm_percent=0.0,
            gain_vs_variant_root_segment_percent=0.0,
            root_baseline_note=idle_baselines.root_baseline_note,
            motor_torque_margin_nm=idle_margin.motor_torque_margin_nm,
            motor_torque_margin_percent=idle_margin.motor_torque_margin_percent,
            torque_margin_note=idle_margin.torque_margin_note,
            motor_coupling_level=MOTOR_COUPLING_LEVEL,
            solver_load_note=SOLVER_LOAD_NOTE,
        )

    operating_point = solve_pythrust_operating_point(
        config, prop_entry, throttle, rho=rho
    )
    rpm = max(0.0, operating_point.rpm)
    omega = rpm * math.pi / 30.0
    aero_eval = compute_foldable_aero_torque(
        omega_rad_s=omega,
        d_aero_m=d_aero_m,
        prop_entry=prop_entry,
        case_id=case_id,
        tip_aero_effectiveness=tip_aero_effectiveness,
        rho=rho,
    )
    aero_torque_nm = aero_eval.aero_torque_nm
    torque_margin = compute_torque_margin(operating_point.torque_nm, aero_eval)

    thrust = evaluate_foldable_thrust_at_state(
        d_aero=d_aero_m,
        context=eval_context,
        prop_entry=prop_entry,
        rpm=rpm,
        rho=rho,
    )
    if case_id == "fixed_25cm_reference":
        thrust = _reference_thrust_evaluation(thrust, eval_context)

    (
        checkpoint_ref,
        current_ref,
        ratio_checkpoint,
        ratio_current,
        basis_note,
    ) = _reference_fields(
        rpm,
        thrust.T_total_pretest_fixed_n,
        case=case_id,
    )

    root_baselines = resolve_root_baselines(
        t_total_pretest=thrust.T_total_pretest_fixed_n,
        rpm=rpm,
        eval_context=eval_context,
        compact_eval_context=compact_eval_context,
        prop_entry=prop_entry,
        rho=rho,
    )

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
    if (
        aero_torque_nm is not None
        and aero_torque_nm > operating_point.torque_nm * 1.05
        and rpm > 0.0
    ):
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
        reference_25cm_at_checkpoint_7100_n=checkpoint_ref,
        reference_25cm_at_current_rpm_n=current_ref,
        ratio_to_checkpoint_25cm_pretest=ratio_checkpoint,
        ratio_to_current_25cm_pretest=ratio_current,
        reference_basis_note=basis_note,
        aero_torque_basis=aero_eval.basis,
        compact_root_20cm_thrust_n=root_baselines.compact_root_20cm_thrust_n,
        variant_root_segment_thrust_n=root_baselines.variant_root_segment_thrust_n,
        gain_vs_compact_root_20cm_percent=root_baselines.gain_vs_compact_root_20cm_percent,
        gain_vs_variant_root_segment_percent=(
            root_baselines.gain_vs_variant_root_segment_percent
        ),
        root_baseline_note=root_baselines.root_baseline_note,
        motor_torque_margin_nm=torque_margin.motor_torque_margin_nm,
        motor_torque_margin_percent=torque_margin.motor_torque_margin_percent,
        torque_margin_note=torque_margin.torque_margin_note,
        motor_coupling_level=MOTOR_COUPLING_LEVEL,
        solver_load_note=SOLVER_LOAD_NOTE,
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
    compact_eval_context = resolve_foldable_evaluation_context(
        apply_calibration_settings(base_config),
        prop_entry,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
        rho=rho,
    )

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
                    compact_eval_context=compact_eval_context,
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
                aero_torque_basis=selected.aero_torque_basis,
                motor_coupling_level=selected.motor_coupling_level,
                solver_load_note=selected.solver_load_note,
            )
        )
    return checkpoints


def run_motor_coupled_7100rpm_interpolated_v2(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    performance_rows: Sequence[MotorCoupledPerformanceRow],
    *,
    evaluation_cases: Sequence[CaseVariantBinding] = MOTOR_COUPLED_EVALUATION_CASES,
    target_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    thrust_split_mode: str = "calibrated_effective_diameter_delta",
    calibration_preset: str = "pretest_70_percent_fixed",
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    rho: float = 1.225,
) -> list[MotorCoupled7100InterpolatedRow]:
    """Interpolate motor scalars at target rpm and evaluate thrust at that rpm."""
    rows: list[MotorCoupled7100InterpolatedRow] = []
    keys = {(row.variant_id, row.case_id) for row in performance_rows}
    compact_eval_context = resolve_foldable_evaluation_context(
        apply_calibration_settings(base_config),
        prop_entry,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=constant_rpm,
        rho=rho,
    )

    for variant_id, case_id, ratio in evaluation_cases:
        if (variant_id, case_id) not in keys:
            continue

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

        case_rows = [
            row
            for row in performance_rows
            if row.variant_id == variant_id and row.case_id == case_id
        ]
        positive = [row for row in case_rows if row.throttle > 0.0]
        interpolated = interpolate_motor_scalars_at_target_rpm(positive, target_rpm)

        thrust = evaluate_foldable_thrust_at_state(
            d_aero=d_aero,
            context=eval_context,
            prop_entry=prop_entry,
            rpm=target_rpm,
            rho=rho,
        )
        if case_id == "fixed_25cm_reference":
            thrust = _reference_thrust_evaluation(thrust, eval_context)

        checkpoint_ref = eval_context.reference_total_25cm_n
        current_ref = reference_25cm_at_rpm_n(
            checkpoint_ref,
            target_rpm,
            checkpoint_rpm=constant_rpm,
        )
        t_pretest = thrust.T_total_pretest_fixed_n
        root_baselines = resolve_root_baselines(
            t_total_pretest=t_pretest,
            rpm=target_rpm,
            eval_context=eval_context,
            compact_eval_context=compact_eval_context,
            prop_entry=prop_entry,
            rho=rho,
        )
        gain = root_baselines.gain_vs_variant_root_segment_percent

        omega = target_rpm * math.pi / 30.0
        aero_eval = compute_foldable_aero_torque(
            omega_rad_s=omega,
            d_aero_m=d_aero,
            prop_entry=prop_entry,
            case_id=case_id,
            tip_aero_effectiveness=tip_eff,
            rho=rho,
        )
        torque_margin = compute_torque_margin(
            interpolated.motor_torque_nm,
            aero_eval,
        )

        max_rpm = max(row.rpm for row in positive) if positive else 0.0
        min_rpm = min(row.rpm for row in positive) if positive else 0.0
        if target_rpm >= constant_rpm - RPM_AT_CHECKPOINT_TOLERANCE:
            if min_rpm <= target_rpm <= max_rpm:
                margin_note = (
                    f"Target {target_rpm:.0f} rpm within sweep "
                    f"[{min_rpm:.0f}, {max_rpm:.0f}]; "
                    f"interpolated throttle={interpolated.interpolated_throttle:.3f}"
                )
            else:
                margin_note = (
                    f"Target {target_rpm:.0f} rpm outside sweep "
                    f"[{min_rpm:.0f}, {max_rpm:.0f}]"
                )
        else:
            margin_note = (
                f"Target {target_rpm:.0f} rpm below checkpoint "
                f"{constant_rpm:.0f}; sweep [{min_rpm:.0f}, {max_rpm:.0f}]"
            )

        rows.append(
            MotorCoupled7100InterpolatedRow(
                case_id=case_id,
                variant_id=variant_id,
                target_rpm=target_rpm,
                interpolated_throttle=interpolated.interpolated_throttle,
                rpm=interpolated.rpm,
                current_a=interpolated.motor_current_a,
                power_w=interpolated.battery_power_w,
                motor_torque_nm=interpolated.motor_torque_nm,
                aero_torque_nm=aero_eval.aero_torque_nm,
                theta_final_deg=theta,
                D_aero_m=d_aero,
                T_root_n=thrust.T_root_n,
                T_total_pretest_fixed_n=t_pretest,
                T_total_target_fixed_n=thrust.T_total_target_fixed_n,
                reference_25cm_at_checkpoint_7100_n=checkpoint_ref,
                reference_25cm_at_current_rpm_n=current_ref,
                ratio_to_checkpoint_25cm_pretest=_ratio_to_reference(
                    t_pretest, checkpoint_ref
                ),
                ratio_to_current_25cm_pretest=_ratio_to_reference(
                    t_pretest, current_ref
                ),
                gain_vs_root_current_rpm_percent=gain,
                motor_margin_note=margin_note,
                interpolation_note=interpolated.interpolation_note,
                aero_torque_basis=aero_eval.basis,
                compact_root_20cm_thrust_n=root_baselines.compact_root_20cm_thrust_n,
                variant_root_segment_thrust_n=root_baselines.variant_root_segment_thrust_n,
                gain_vs_compact_root_20cm_percent=(
                    root_baselines.gain_vs_compact_root_20cm_percent
                ),
                gain_vs_variant_root_segment_percent=(
                    root_baselines.gain_vs_variant_root_segment_percent
                ),
                root_baseline_note=root_baselines.root_baseline_note,
                motor_torque_margin_nm=torque_margin.motor_torque_margin_nm,
                motor_torque_margin_percent=torque_margin.motor_torque_margin_percent,
                torque_margin_note=torque_margin.torque_margin_note,
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )
    return rows


def run_motor_coupled_reference_consistency_v2(
    performance_rows: Sequence[MotorCoupledPerformanceRow],
    interpolated_rows: Sequence[MotorCoupled7100InterpolatedRow],
    *,
    current_operating_throttle: float = 0.70,
    root_case_id: str = "root_only_20cm",
    root_variant_id: str = "TIP_HINGED_250_V02",
    deployed_case_id: str = "bias10_k0.25_s5",
    deployed_variant_id: str = "TIP_HINGED_250_RT65_35",
    latch_case_id: str = "latch_theta0",
    latch_variant_id: str = "TIP_HINGED_250_V02",
    checkpoint_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
) -> list[MotorCoupledReferenceConsistencyRow]:
    """Summary rows separating checkpoint vs current-rpm reference bases."""
    summary: list[MotorCoupledReferenceConsistencyRow] = []

    def _row_at_throttle(
        variant_id: str,
        case_id: str,
        throttle: float,
    ) -> MotorCoupledPerformanceRow | None:
        matches = [
            row
            for row in performance_rows
            if row.variant_id == variant_id
            and row.case_id == case_id
            and abs(row.throttle - throttle) < 1e-6
        ]
        return matches[0] if matches else None

    def _interp_row(
        variant_id: str,
        case_id: str,
    ) -> MotorCoupled7100InterpolatedRow | None:
        matches = [
            row
            for row in interpolated_rows
            if row.variant_id == variant_id and row.case_id == case_id
        ]
        return matches[0] if matches else None

    root_row = _row_at_throttle(root_variant_id, root_case_id, current_operating_throttle)
    deployed_row = _row_at_throttle(
        deployed_variant_id, deployed_case_id, current_operating_throttle
    )
    deployed_interp = _interp_row(deployed_variant_id, deployed_case_id)
    latch_interp = _interp_row(latch_variant_id, latch_case_id)

    if root_row is not None:
        summary.append(
            MotorCoupledReferenceConsistencyRow(
                row_type="root_only_at_current_rpm",
                rpm=root_row.rpm,
                thrust_n=root_row.T_total_pretest_fixed_n,
                reference_basis="motor_coupled @ throttle 0.70",
                interpretation_note=(
                    "Root-only baseline at motor equilibrium rpm (~6547), "
                    "not checkpoint 7100"
                ),
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )
    if deployed_row is not None:
        summary.append(
            MotorCoupledReferenceConsistencyRow(
                row_type="deployed_candidate_at_current_rpm",
                rpm=deployed_row.rpm,
                thrust_n=deployed_row.T_total_pretest_fixed_n,
                reference_basis="motor_coupled @ throttle 0.70",
                interpretation_note=(
                    "Best no-latch candidate RT65_35 bias10_k0.25_s5 at "
                    "motor equilibrium rpm"
                ),
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )
        summary.append(
            MotorCoupledReferenceConsistencyRow(
                row_type="reference_25cm_at_current_rpm",
                rpm=deployed_row.rpm,
                thrust_n=deployed_row.reference_25cm_at_current_rpm_n,
                reference_basis="n² proxy from checkpoint 7100",
                interpretation_note=(
                    "Same-RPM 25 cm reference estimate; not experimental "
                    "measurement at this rpm"
                ),
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )

    ref_checkpoint = (
        root_row.reference_25cm_at_checkpoint_7100_n
        if root_row is not None
        else (
            deployed_row.reference_25cm_at_checkpoint_7100_n
            if deployed_row is not None
            else 0.0
        )
    )
    summary.append(
        MotorCoupledReferenceConsistencyRow(
            row_type="reference_25cm_at_checkpoint_7100",
            rpm=checkpoint_rpm,
            thrust_n=ref_checkpoint,
            reference_basis="engineering checkpoint prescribed rpm",
            interpretation_note=(
                "Fixed 25 cm reference at 7100 rpm used for checkpoint "
                "ratio comparisons"
            ),
            motor_coupling_level=MOTOR_COUPLING_LEVEL,
            solver_load_note=SOLVER_LOAD_NOTE,
        )
    )

    if deployed_interp is not None:
        summary.append(
            MotorCoupledReferenceConsistencyRow(
                row_type="deployed_candidate_interpolated_at_7100",
                rpm=deployed_interp.rpm,
                thrust_n=deployed_interp.T_total_pretest_fixed_n,
                reference_basis=(
                    f"interpolated throttle {deployed_interp.interpolated_throttle:.3f}"
                ),
                interpretation_note=(
                    "RT65_35 bias10_k0.25_s5 thrust evaluated at 7100 rpm with "
                    "interpolated motor scalars"
                ),
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )
    if latch_interp is not None:
        summary.append(
            MotorCoupledReferenceConsistencyRow(
                row_type="latch_candidate_interpolated_at_7100",
                rpm=latch_interp.rpm,
                thrust_n=latch_interp.T_total_pretest_fixed_n,
                reference_basis=(
                    f"interpolated throttle {latch_interp.interpolated_throttle:.3f}"
                ),
                interpretation_note=(
                    "Latch_theta0 thrust evaluated at 7100 rpm with "
                    "interpolated motor scalars"
                ),
                motor_coupling_level=MOTOR_COUPLING_LEVEL,
                solver_load_note=SOLVER_LOAD_NOTE,
            )
        )

    summary.append(
        MotorCoupledReferenceConsistencyRow(
            row_type="reference_25cm_at_7100",
            rpm=checkpoint_rpm,
            thrust_n=ref_checkpoint,
            reference_basis="engineering checkpoint prescribed rpm",
            interpretation_note=(
                "Same checkpoint reference as reference_25cm_at_checkpoint_7100"
            ),
            motor_coupling_level=MOTOR_COUPLING_LEVEL,
            solver_load_note=SOLVER_LOAD_NOTE,
        )
    )
    return summary


def run_motor_coupled_consistency_audit_v2(
    performance_rows: Sequence[MotorCoupledPerformanceRow],
    interpolated_rows: Sequence[MotorCoupled7100InterpolatedRow],
    *,
    current_operating_throttle: float = 0.70,
) -> list[MotorCoupledConsistencyAuditRow]:
    """Audit motor-coupled output consistency checks."""
    audits: list[MotorCoupledConsistencyAuditRow] = []

    root_interp = next(
        (row for row in interpolated_rows if row.case_id == "root_only_20cm"),
        None,
    )
    rt65_interp = next(
        (
            row
            for row in interpolated_rows
            if row.case_id == "bias10_k0.25_s5"
            and row.variant_id == "TIP_HINGED_250_RT65_35"
        ),
        None,
    )
    deployed_row = next(
        (
            row
            for row in performance_rows
            if row.case_id == "bias10_k0.25_s5"
            and row.variant_id == "TIP_HINGED_250_RT65_35"
            and abs(row.throttle - current_operating_throttle) < 1e-6
        ),
        None,
    )
    latch_interp = next(
        (row for row in interpolated_rows if row.case_id == "latch_theta0"),
        None,
    )

    if root_interp is not None:
        root_ok = (
            root_interp.aero_torque_basis == "foldable_proxy"
            and root_interp.aero_torque_nm is not None
            and root_interp.aero_torque_nm > 0.0
        )
        audits.append(
            MotorCoupledConsistencyAuditRow(
                check_id="aero_torque_root_only_check",
                status="pass" if root_ok else "fail",
                value=(
                    f"basis={root_interp.aero_torque_basis}; "
                    f"torque={root_interp.aero_torque_nm}"
                ),
                expected_behavior=(
                    "root_only aero torque computed via foldable_proxy, not silent 0"
                ),
                note="Uses D_aero=0.20 m with full root effectiveness",
            )
        )

    if rt65_interp is not None:
        gain_compact = rt65_interp.gain_vs_compact_root_20cm_percent
        gain_variant = rt65_interp.gain_vs_variant_root_segment_percent
        compact_ok = 60.0 <= gain_compact <= 85.0
        audits.append(
            MotorCoupledConsistencyAuditRow(
                check_id="baseline_gain_rt65_check",
                status="pass" if compact_ok else "fail",
                value=(
                    f"gain_vs_compact_root={gain_compact:.1f}%; "
                    f"gain_vs_variant_root={gain_variant:.1f}%"
                ),
                expected_behavior=(
                    "RT65_35 gain vs compact 20 cm ~70%; variant gain may be larger"
                ),
                note=rt65_interp.root_baseline_note,
            )
        )

    if deployed_row is not None:
        ref_ok = (
            deployed_row.reference_25cm_at_current_rpm_n
            < deployed_row.reference_25cm_at_checkpoint_7100_n
        )
        audits.append(
            MotorCoupledConsistencyAuditRow(
                check_id="reference_basis_check",
                status="pass" if ref_ok else "fail",
                value=(
                    f"checkpoint={deployed_row.reference_25cm_at_checkpoint_7100_n:.3f}; "
                    f"current={deployed_row.reference_25cm_at_current_rpm_n:.3f}"
                ),
                expected_behavior=(
                    "checkpoint and current-rpm references remain separated at 6547 rpm"
                ),
                note=deployed_row.reference_basis_note,
            )
        )

    coupling_ok = all(
        row.motor_coupling_level == MOTOR_COUPLING_LEVEL for row in performance_rows
    ) and all(row.motor_coupling_level == MOTOR_COUPLING_LEVEL for row in interpolated_rows)
    audits.append(
        MotorCoupledConsistencyAuditRow(
            check_id="coupling_level_check",
            status="pass" if coupling_ok else "fail",
            value=MOTOR_COUPLING_LEVEL,
            expected_behavior="all rows use reference_load_postprocess",
            note=SOLVER_LOAD_NOTE,
        )
    )

    if latch_interp is not None:
        margin_ok = (
            latch_interp.torque_margin_note != "not_computed"
            and latch_interp.motor_torque_margin_nm is not None
        )
        audits.append(
            MotorCoupledConsistencyAuditRow(
                check_id="torque_margin_check",
                status="pass" if margin_ok else "fail",
                value=latch_interp.torque_margin_note,
                expected_behavior=(
                    "torque margin computed at interpolated 7100 rpm when aero known"
                ),
                note=(
                    f"motor={latch_interp.motor_torque_nm:.4f} Nm; "
                    f"aero={latch_interp.aero_torque_nm}"
                ),
            )
        )

    return audits


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


def write_motor_coupled_7100rpm_interpolated_v2_csv(
    path: str,
    rows: Sequence[MotorCoupled7100InterpolatedRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(MOTOR_COUPLED_7100RPM_INTERPOLATED_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_motor_coupled_reference_consistency_v2_csv(
    path: str,
    rows: Sequence[MotorCoupledReferenceConsistencyRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(MOTOR_COUPLED_REFERENCE_CONSISTENCY_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_motor_coupled_consistency_audit_v2_csv(
    path: str,
    rows: Sequence[MotorCoupledConsistencyAuditRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(MOTOR_COUPLED_CONSISTENCY_AUDIT_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
