"""Tests for V1 dynamic spin-up skeleton."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics import (
    SPINUP_CSV_COLUMNS,
    SpinUpConfig,
    run_spinup_simulation,
    write_spinup_csv,
)
from pythrust.foldable.models import load_config
from pythrust.foldable.variants import make_variant_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
PROP_DB_PATH = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def rt75_spinup_states():
    config = load_config(CONFIG_PATH)
    variant = make_variant_config(config, 75, 25)
    db = PropellerDatabase()
    db.load(PROP_DB_PATH, strict=False)
    prop_entry = db.get(variant.reference_propeller_id)
    if prop_entry is None:
        pytest.skip("Reference propeller not available in database")
    return run_spinup_simulation(
        variant,
        prop_entry,
        spinup=SpinUpConfig(dt_s=0.01, t_end_s=3.0),
    )


def test_first_row_rpm_zero(rt75_spinup_states) -> None:
    assert rt75_spinup_states[0].rpm == pytest.approx(0.0)


def test_first_row_thrust_zero(rt75_spinup_states) -> None:
    assert rt75_spinup_states[0].thrust_n == pytest.approx(0.0)


def test_first_row_theta_folded(rt75_spinup_states) -> None:
    config = load_config(CONFIG_PATH)
    assert rt75_spinup_states[0].theta_deg == pytest.approx(config.hinge.theta_min_deg)


def test_rpm_increases_after_motor_command(rt75_spinup_states) -> None:
    assert max(state.rpm for state in rt75_spinup_states) > rt75_spinup_states[0].rpm


def test_theta_opens_in_expected_direction(rt75_spinup_states) -> None:
    initial_theta = rt75_spinup_states[0].theta_deg
    max_theta = max(state.theta_deg for state in rt75_spinup_states)
    assert max_theta > initial_theta


def test_csv_columns_exist(rt75_spinup_states, tmp_path: Path) -> None:
    csv_path = write_spinup_csv(tmp_path / "dynamic_spinup_RT75_25.csv", rt75_spinup_states)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(SPINUP_CSV_COLUMNS)
        rows = list(reader)
    assert len(rows) == len(rt75_spinup_states)
