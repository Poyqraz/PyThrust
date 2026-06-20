"""Tests for V2 physics stability diagnostics."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics import (
    STABILITY_REPORT_COLUMNS,
    PrescribedRpmConfig,
    analyze_physics_stability,
    quasi_static_equilibrium_theta_deg,
    run_dt_sensitivity_cases,
    run_hinge_parameter_diagnostic_sweep,
    run_prescribed_rpm_physics,
    scaled_hinge_config,
    write_stability_report,
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


def test_stability_report_columns(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    states = run_prescribed_rpm_physics(
        config,
        prop,
        sim=PrescribedRpmConfig(dt_s=0.01, t_end_s=0.5, constant_rpm=7100.0),
    )
    metrics = analyze_physics_stability(
        states,
        config,
        case_id="test_case",
        rpm_profile="constant_7100",
        dt_s=0.01,
    )
    path = tmp_path / "prescribed_rpm_stability_report.csv"
    write_stability_report(str(path), [metrics])
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(STABILITY_REPORT_COLUMNS)
        rows = list(reader)
    assert len(rows) == 1


def test_quasi_static_equilibrium_near_dynamic_final(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    states = run_prescribed_rpm_physics(
        config,
        prop,
        sim=PrescribedRpmConfig(dt_s=0.001, t_end_s=2.0, constant_rpm=7100.0),
    )
    eq = quasi_static_equilibrium_theta_deg(7100.0, config)
    assert eq is not None
    final_theta = states[-1].theta_deg
    assert final_theta == pytest.approx(eq, abs=5.0)


def test_dt_sensitivity_runs_three_cases(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    cases = run_dt_sensitivity_cases(config, prop, t_end_s=0.5)
    assert len(cases) == 3


def test_stiction_reduces_chatter(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    states = run_prescribed_rpm_physics(
        config,
        prop,
        sim=PrescribedRpmConfig(dt_s=0.001, t_end_s=2.0, constant_rpm=7100.0),
    )
    metrics = analyze_physics_stability(
        states,
        config,
        case_id="chatter_check",
        rpm_profile="constant_7100",
        dt_s=0.001,
    )
    assert metrics.theta_dot_rms_last_20_percent < 10.0


def test_diagnostic_sweep_subset(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_hinge_parameter_diagnostic_sweep(
        config,
        prop,
        dt_s=0.01,
        t_end_s=0.3,
    )
    assert len(rows) == 27
