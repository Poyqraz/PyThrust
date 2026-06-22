"""Tests for prescribed-RPM physics simulation."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics import (
    PHYSICS_DEBUG_CSV_COLUMNS,
    PrescribedRpmConfig,
    run_prescribed_rpm_physics,
    write_physics_csv,
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


def test_constant_rpm_matches_input(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    sim = PrescribedRpmConfig(dt_s=0.01, t_end_s=0.5, constant_rpm=7100.0)
    states = run_prescribed_rpm_physics(config, prop, sim=sim)
    assert states
    assert all(s.rpm == pytest.approx(7100.0) for s in states[1:])


def test_ramp_rpm_profile(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    sim = PrescribedRpmConfig(
        dt_s=0.01,
        t_end_s=0.5,
        rpm_mode="ramp",
        ramp_rpm_end=7100.0,
        ramp_time_s=0.5,
    )
    states = run_prescribed_rpm_physics(config, prop, sim=sim)
    assert states[-1].rpm == pytest.approx(7100.0, rel=0.05)
    assert states[0].rpm == pytest.approx(0.0)


def test_physics_csv_columns(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    sim = PrescribedRpmConfig(dt_s=0.01, t_end_s=0.2, constant_rpm=7100.0)
    states = run_prescribed_rpm_physics(config, prop, sim=sim)
    path = write_physics_csv(tmp_path / "physics_debug.csv", states)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(PHYSICS_DEBUG_CSV_COLUMNS)
        rows = list(reader)
    assert len(rows) == len(states)


def test_folded_start_and_root_thrust(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    sim = PrescribedRpmConfig(dt_s=0.001, t_end_s=0.01, constant_rpm=7100.0)
    states = run_prescribed_rpm_physics(config, prop, sim=sim)
    first = states[0]
    assert first.theta_deg == pytest.approx(config.hinge.theta_min_deg)
    assert first.thrust_root_n > 0.0
    assert first.thrust_tip_n == pytest.approx(0.0, abs=1e-4)


def test_opening_slower_than_instant(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    sim = PrescribedRpmConfig(dt_s=0.001, t_end_s=0.05, constant_rpm=7100.0)
    states = run_prescribed_rpm_physics(config, prop, sim=sim)
    assert states[-1].theta_deg < 0.0
