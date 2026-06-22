"""Tests for motor-coupled foldable V2 performance."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.motor_coupled_performance import (
    MOTOR_COUPLED_7100RPM_CHECKPOINT_V2_COLUMNS,
    MOTOR_COUPLED_7100RPM_INTERPOLATED_V2_COLUMNS,
    MOTOR_COUPLED_CONSISTENCY_AUDIT_V2_COLUMNS,
    MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS,
    MOTOR_COUPLED_REFERENCE_CONSISTENCY_V2_COLUMNS,
    MOTOR_COUPLING_LEVEL,
    DEFAULT_TARGET_CHECKPOINT_RPM,
    interpolate_motor_scalars_at_target_rpm,
    reference_25cm_at_rpm_n,
    run_motor_coupled_7100rpm_checkpoint_v2,
    run_motor_coupled_7100rpm_interpolated_v2,
    run_motor_coupled_consistency_audit_v2,
    run_motor_coupled_foldable_performance_v2,
    run_motor_coupled_reference_consistency_v2,
    write_motor_coupled_7100rpm_checkpoint_v2_csv,
    write_motor_coupled_7100rpm_interpolated_v2_csv,
    write_motor_coupled_consistency_audit_v2_csv,
    write_motor_coupled_foldable_performance_v2_csv,
    write_motor_coupled_reference_consistency_v2_csv,
)
from pythrust.foldable.models import load_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
PROP_DB = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def v02_physics_setup():
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROP_DB, strict=False)
    prop = db.get(config.reference_propeller_id)
    if prop is None:
        pytest.skip("Reference propeller not available")
    return config, prop


def test_motor_coupled_performance_columns(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.0, 0.5, 1.0),
    )
    assert len(rows) == 5 * 3
    path = tmp_path / "motor_coupled_foldable_performance_v2.csv"
    write_motor_coupled_foldable_performance_v2_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS)


def test_rpm_increases_with_throttle(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        evaluation_cases=(("TIP_HINGED_250_V02", "latch_theta0", None),),
        t_end_s=0.3,
        throttle_values=(0.3, 0.6, 1.0),
    )
    rpms = [row.rpm for row in rows if row.throttle > 0.0]
    assert rpms == sorted(rpms)
    assert all(row.motor_current_a >= 0.0 for row in rows)
    assert all(row.battery_power_w >= 0.0 for row in rows)


def test_calibrated_thrust_not_above_ideal(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7, 1.0),
    )
    for row in rows:
        if row.throttle <= 0.0 or row.case_id == "fixed_25cm_reference":
            continue
        assert row.T_total_pretest_fixed_n <= row.T_total_ideal_delta_n + 1e-6
        assert row.T_total_target_fixed_n <= row.T_total_ideal_delta_n + 1e-6


def test_root_only_below_foldable_cases(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(1.0,),
    )
    root = next(
        row
        for row in rows
        if row.case_id == "root_only_20cm" and row.throttle == 1.0
    )
    latch = next(
        row
        for row in rows
        if row.case_id == "latch_theta0" and row.throttle == 1.0
    )
    assert root.T_total_pretest_fixed_n < latch.T_total_pretest_fixed_n


def test_7100_checkpoint_csv(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.5, 0.7, 0.85, 1.0),
    )
    checkpoint_rows = run_motor_coupled_7100rpm_checkpoint_v2(perf_rows)
    assert len(checkpoint_rows) == 5
    assert all(row.motor_margin_note for row in checkpoint_rows)
    path = tmp_path / "motor_coupled_7100rpm_checkpoint_v2.csv"
    write_motor_coupled_7100rpm_checkpoint_v2_csv(str(path), checkpoint_rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_7100RPM_CHECKPOINT_V2_COLUMNS)


def test_interpolation_returns_row_at_7100(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.5, 0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    assert len(interp_rows) == 5
    latch = next(row for row in interp_rows if row.case_id == "latch_theta0")
    assert latch.target_rpm == DEFAULT_TARGET_CHECKPOINT_RPM
    assert latch.rpm == pytest.approx(DEFAULT_TARGET_CHECKPOINT_RPM, rel=1e-6)
    assert "interpolation" in latch.interpolation_note.lower()


def test_interpolated_throttle_between_070_and_100(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.5, 0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    for row in interp_rows:
        if row.case_id == "fixed_25cm_reference":
            continue
        assert 0.70 <= row.interpolated_throttle <= 1.00


def test_current_rpm_reference_lower_than_checkpoint(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        evaluation_cases=(("TIP_HINGED_250_V02", "latch_theta0", None),),
        t_end_s=0.3,
        throttle_values=(0.7,),
    )
    row = rows[0]
    assert row.rpm < DEFAULT_TARGET_CHECKPOINT_RPM
    assert (
        row.reference_25cm_at_current_rpm_n
        < row.reference_25cm_at_checkpoint_7100_n
    )


def test_ratio_to_current_differs_from_checkpoint_when_rpm_not_7100(
    v02_physics_setup,
) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        evaluation_cases=(("TIP_HINGED_250_RT65_35", "bias10_k0.25_s5", (65, 35)),),
        t_end_s=0.3,
        throttle_values=(0.7,),
    )
    row = rows[0]
    assert abs(row.rpm - DEFAULT_TARGET_CHECKPOINT_RPM) > 100.0
    assert row.ratio_to_current_25cm_pretest != pytest.approx(
        row.ratio_to_checkpoint_25cm_pretest, rel=1e-3
    )
    assert row.ratio_to_current_25cm_pretest > row.ratio_to_checkpoint_25cm_pretest


def test_reference_25cm_n2_scaling() -> None:
    checkpoint = 9.10
    rpm = 6547.0
    scaled = reference_25cm_at_rpm_n(checkpoint, rpm, checkpoint_rpm=7100.0)
    expected = checkpoint * (rpm / 7100.0) ** 2
    assert scaled == pytest.approx(expected, rel=1e-6)
    assert scaled < checkpoint


def test_interpolated_and_consistency_csv(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.5, 0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    consistency_rows = run_motor_coupled_reference_consistency_v2(
        perf_rows, interp_rows
    )
    interp_path = tmp_path / "motor_coupled_7100rpm_interpolated_v2.csv"
    consistency_path = tmp_path / "motor_coupled_reference_consistency_v2.csv"
    write_motor_coupled_7100rpm_interpolated_v2_csv(str(interp_path), interp_rows)
    write_motor_coupled_reference_consistency_v2_csv(
        str(consistency_path), consistency_rows
    )
    with interp_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_7100RPM_INTERPOLATED_V2_COLUMNS)
    with consistency_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_REFERENCE_CONSISTENCY_V2_COLUMNS)
    row_types = {row.row_type for row in consistency_rows}
    assert "root_only_at_current_rpm" in row_types
    assert "reference_25cm_at_checkpoint_7100" in row_types
    assert "deployed_candidate_interpolated_at_7100" in row_types


def test_performance_csv_has_reference_columns(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7,),
    )
    path = tmp_path / "motor_coupled_foldable_performance_v2.csv"
    write_motor_coupled_foldable_performance_v2_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS)
        first = next(reader)
        assert "reference_25cm_at_checkpoint_7100_n" in first
        assert "reference_basis_note" in first
        assert first["reference_basis_note"]


def test_root_only_aero_torque_not_silent_zero(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7,),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    root = next(row for row in interp_rows if row.case_id == "root_only_20cm")
    assert root.aero_torque_basis == "foldable_proxy"
    assert root.aero_torque_nm is not None
    assert root.aero_torque_nm > 0.0


def test_separate_root_baseline_gains(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    rt65 = next(
        row
        for row in interp_rows
        if row.case_id == "bias10_k0.25_s5"
        and row.variant_id == "TIP_HINGED_250_RT65_35"
    )
    assert rt65.gain_vs_compact_root_20cm_percent == pytest.approx(70.0, abs=5.0)
    assert rt65.gain_vs_variant_root_segment_percent > 150.0
    assert "internal geometry" in rt65.root_baseline_note


def test_motor_coupling_level_and_torque_margin(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    for row in perf_rows:
        assert row.motor_coupling_level == MOTOR_COUPLING_LEVEL
        assert row.solver_load_note
    latch = next(row for row in interp_rows if row.case_id == "latch_theta0")
    assert latch.motor_coupling_level == "reference_load_postprocess"
    assert latch.torque_margin_note != "not_computed"
    assert latch.motor_torque_margin_nm is not None
    assert latch.motor_torque_margin_percent is not None


def test_consistency_audit_csv(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    perf_rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        t_end_s=0.3,
        throttle_values=(0.7, 0.85, 1.0),
    )
    interp_rows = run_motor_coupled_7100rpm_interpolated_v2(
        config, prop, perf_rows, t_end_s=0.3
    )
    audit_rows = run_motor_coupled_consistency_audit_v2(perf_rows, interp_rows)
    assert len(audit_rows) == 5
    assert all(row.status == "pass" for row in audit_rows)
    path = tmp_path / "motor_coupled_consistency_audit_v2.csv"
    write_motor_coupled_consistency_audit_v2_csv(str(path), audit_rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(MOTOR_COUPLED_CONSISTENCY_AUDIT_V2_COLUMNS)


def test_reference_separation_preserved(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_motor_coupled_foldable_performance_v2(
        config,
        prop,
        evaluation_cases=(("TIP_HINGED_250_RT65_35", "bias10_k0.25_s5", (65, 35)),),
        t_end_s=0.3,
        throttle_values=(0.7,),
    )
    row = rows[0]
    assert row.reference_25cm_at_current_rpm_n < row.reference_25cm_at_checkpoint_7100_n
    assert row.ratio_to_current_25cm_pretest != pytest.approx(
        row.ratio_to_checkpoint_25cm_pretest, rel=1e-3
    )
