"""Tests for alternative thrust split modes."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.split_thrust import (
    THRUST_SPLIT_MODES,
    compute_split_thrust,
)
from pythrust.foldable.models import load_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
PROP_DB = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def v02_prop():
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROP_DB, strict=False)
    prop = db.get(config.reference_propeller_id)
    if prop is None:
        pytest.skip("Reference propeller not available")
    return config, prop


def test_independent_tip_disk_default(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    assert result.thrust_total_n == pytest.approx(
        result.thrust_root_n + result.thrust_tip_n
    )


def test_effective_diameter_delta_exceeds_independent_at_open(v02_prop) -> None:
    config, prop = v02_prop
    common = dict(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    independent = compute_split_thrust(**common, split_mode="independent_tip_disk")
    delta = compute_split_thrust(**common, split_mode="effective_diameter_delta")
    assert delta.thrust_tip_n > independent.thrust_tip_n
    assert delta.thrust_total_n > independent.thrust_total_n


def test_annular_proxy_full_open_fraction(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
        split_mode="annular_extension_proxy",
    )
    fraction = result.thrust_tip_n / result.thrust_total_n
    assert fraction > 0.1


def test_delta_zero_tip_when_folded(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=-180.0,
        tip_aero_effectiveness=0.0,
        config=config,
        prop_entry=prop,
        split_mode="effective_diameter_delta",
    )
    assert result.thrust_tip_n == pytest.approx(0.0, abs=1e-9)


def test_thrust_split_comparison_csv(v02_prop, tmp_path: Path) -> None:
    from pythrust.foldable.dynamics.physics_thrust_split_diagnostic import (
        THRUST_SPLIT_COMPARISON_COLUMNS,
        run_thrust_split_model_comparison,
        write_thrust_split_model_comparison_csv,
    )

    config, prop = v02_prop
    rows = run_thrust_split_model_comparison(config, prop, t_end_s=0.3)
    assert len(rows) == 4 * len(THRUST_SPLIT_MODES)
    path = tmp_path / "thrust_split_model_comparison.csv"
    write_thrust_split_model_comparison_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(THRUST_SPLIT_COMPARISON_COLUMNS)
