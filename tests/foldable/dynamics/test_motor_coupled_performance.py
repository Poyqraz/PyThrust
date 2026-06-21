"""Tests for motor-coupled foldable V2 performance."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.motor_coupled_performance import (
    MOTOR_COUPLED_7100RPM_CHECKPOINT_V2_COLUMNS,
    MOTOR_COUPLED_FOLDABLE_PERFORMANCE_V2_COLUMNS,
    run_motor_coupled_7100rpm_checkpoint_v2,
    run_motor_coupled_foldable_performance_v2,
    write_motor_coupled_7100rpm_checkpoint_v2_csv,
    write_motor_coupled_foldable_performance_v2_csv,
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
