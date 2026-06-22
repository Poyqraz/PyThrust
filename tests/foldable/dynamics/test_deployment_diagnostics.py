"""Tests for deployment sweep and tip thrust activation diagnostics."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from pythrust.foldable.dynamics import (
    DEPLOYMENT_BIAS_STIFFNESS_SWEEP_COLUMNS,
    TIP_THRUST_ACTIVATION_COLUMNS,
    compute_tip_thrust_breakdown,
    run_deployment_bias_stiffness_sweep,
    run_open_latch_diagnostic_cases,
    run_tip_thrust_activation_diagnostic,
    write_deployment_bias_stiffness_sweep_csv,
    write_tip_thrust_activation_csv,
)
from pythrust.foldable.dynamics.hinge_dynamics import initial_hinge_state, integrate_hinge_step
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


def test_deployment_sweep_subset(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    rows = run_deployment_bias_stiffness_sweep(
        config,
        prop,
        bias_values=(0.0, 10.0),
        stiffness_multipliers=(1.0, 0.25),
        moment_scales=(1.0, 2.0),
        t_end_s=0.3,
    )
    assert len(rows) == 8
    row = rows[0]
    assert row.T_total_ideal_delta_n == pytest.approx(
        row.T_root_n + row.T_tip_ideal_delta_n, rel=1e-6
    )
    assert row.T_total_pretest_fixed_n == pytest.approx(
        row.T_root_n + row.T_tip_pretest_fixed_n, rel=1e-6
    )
    path = tmp_path / "deployment_bias_stiffness_sweep.csv"
    write_deployment_bias_stiffness_sweep_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(DEPLOYMENT_BIAS_STIFFNESS_SWEEP_COLUMNS)


def test_foldable_performance_summary_v2(v02_physics_setup, tmp_path: Path) -> None:
    from pythrust.foldable.dynamics import (
        FOLDABLE_PERFORMANCE_SUMMARY_V2_COLUMNS,
        run_foldable_performance_summary_v2,
        write_foldable_performance_summary_v2_csv,
    )

    config, prop = v02_physics_setup
    rows = run_foldable_performance_summary_v2(config, prop, t_end_s=0.3)
    assert len(rows) == 14
    labels = {row.decision_label for row in rows if row.decision_label}
    assert "compact_root_baseline" in labels
    assert "current_pretest_candidate" in labels
    assert "target_candidate" in labels
    path = tmp_path / "foldable_performance_summary_v2.csv"
    write_foldable_performance_summary_v2_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(FOLDABLE_PERFORMANCE_SUMMARY_V2_COLUMNS)


def test_partial_deployment_pretest_below_latch(v02_physics_setup) -> None:
    from pythrust.foldable.dynamics import run_foldable_performance_summary_v2

    config, prop = v02_physics_setup
    rows = run_foldable_performance_summary_v2(config, prop, t_end_s=0.3)
    latch = next(
        r
        for r in rows
        if r.case_id == "latch_theta0" and r.thrust_model_level == "pretest_70_fixed"
    )
    bias = next(
        r
        for r in rows
        if r.case_id == "bias10_k0.25_s5" and r.thrust_model_level == "pretest_70_fixed"
    )
    assert bias.T_total_n < latch.T_total_n
    assert bias.ratio_to_25cm_reference < latch.ratio_to_25cm_reference


def test_open_latch_reaches_open_stop(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_open_latch_diagnostic_cases(config, prop, t_end_s=0.5)
    assert any(r.reaches_open_stop_flag for r in rows)


def test_tip_thrust_breakdown_d4_scaling(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    folded = compute_tip_thrust_breakdown(
        rpm=7100.0,
        theta_deg=-180.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    open_case = compute_tip_thrust_breakdown(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    assert folded.thrust_tip_raw_n == pytest.approx(0.0)
    assert open_case.thrust_tip_raw_n > folded.thrust_tip_raw_n


def test_tip_activation_diagnostic_subset(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    rows = run_tip_thrust_activation_diagnostic(
        config,
        prop,
        t_end_s=0.3,
    )
    assert len(rows) == 18
    path = tmp_path / "tip_thrust_activation_diagnostic.csv"
    write_tip_thrust_activation_csv(str(path), rows[:2])
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(TIP_THRUST_ACTIVATION_COLUMNS)


def test_open_latch_holds_at_theta_max(v02_physics_setup) -> None:
    config, _prop = v02_physics_setup
    cfg = replace(
        config,
        hinge=replace(
            config.hinge,
            initial_stow_offset_deg=175.0,
            open_latch_diagnostic=True,
            open_latch_capture_deg=5.0,
        ),
    )
    state = initial_hinge_state(cfg)
    assert state.theta_deg == pytest.approx(-5.0, abs=0.1)
    state = integrate_hinge_step(
        state,
        dt_s=0.001,
        rpm=7100.0,
        tip_thrust_n=0.0,
        config=cfg,
    )
    assert state.theta_deg == pytest.approx(0.0, abs=0.1)
    assert state.theta_dot_deg_s == pytest.approx(0.0, abs=1.0)
