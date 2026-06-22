"""Tests for split root/tip thrust model."""

from __future__ import annotations

import pytest

from pythrust.foldable.dynamics.split_thrust import compute_split_thrust
from pythrust.foldable.models import load_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]
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


def test_root_thrust_positive_at_rpm(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=-180.0,
        tip_aero_effectiveness=0.0,
        config=config,
        prop_entry=prop,
    )
    assert result.thrust_root_n > 0.0


def test_tip_thrust_near_zero_when_folded(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=-180.0,
        tip_aero_effectiveness=0.0,
        config=config,
        prop_entry=prop,
    )
    assert result.thrust_tip_n == pytest.approx(0.0, abs=1e-6)


def test_tip_thrust_grows_with_opening(v02_prop) -> None:
    config, prop = v02_prop
    folded = compute_split_thrust(
        rpm=7100.0,
        theta_deg=-180.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    open_ = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=config,
        prop_entry=prop,
    )
    assert open_.thrust_tip_n > folded.thrust_tip_n


def test_total_equals_sum(v02_prop) -> None:
    config, prop = v02_prop
    result = compute_split_thrust(
        rpm=5000.0,
        theta_deg=-45.0,
        tip_aero_effectiveness=0.5,
        config=config,
        prop_entry=prop,
    )
    assert result.thrust_total_n == pytest.approx(
        result.thrust_root_n + result.thrust_tip_n
    )
