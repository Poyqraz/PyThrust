"""Tests for alternative thrust split modes."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.split_thrust import (
    THRUST_SPLIT_MODES,
    _thrust_from_diameter,
    compute_split_thrust,
)
from pythrust.foldable.dynamics.thrust_split_calibration import (
    tip_delta_efficiency_factor_for_preset,
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


def test_calibrated_pretest_fixed_hits_reference_fraction_at_open(v02_prop) -> None:
    config, prop = v02_prop
    d_open = config.geometry.diameter_open_m
    scale = config.calibration.k_thrust
    reference = _thrust_from_diameter(
        7100.0, d_open, prop, rho=1.225, scale=scale
    )

    pretest_config = replace(
        config,
        calibration=replace(
            config.calibration,
            thrust_split_mode="calibrated_effective_diameter_delta",
            tip_delta_calibration_preset="pretest_70_percent_fixed",
        ),
    )
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=pretest_config,
        prop_entry=prop,
    )
    assert result.thrust_total_n == pytest.approx(reference * 0.70, rel=1e-4)


def test_calibrated_target_fixed_hits_reference_fraction_at_open(v02_prop) -> None:
    config, prop = v02_prop
    d_open = config.geometry.diameter_open_m
    scale = config.calibration.k_thrust
    reference = _thrust_from_diameter(
        7100.0, d_open, prop, rho=1.225, scale=scale
    )

    target_config = replace(
        config,
        calibration=replace(
            config.calibration,
            thrust_split_mode="calibrated_effective_diameter_delta",
            tip_delta_calibration_preset="target_85_percent_fixed",
        ),
    )
    result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=target_config,
        prop_entry=prop,
    )
    assert result.thrust_total_n == pytest.approx(reference * 0.85, rel=1e-4)


def test_calibrated_partial_deployment_below_pretest_at_open(v02_prop) -> None:
    config, prop = v02_prop
    d_open = config.geometry.diameter_open_m
    scale = config.calibration.k_thrust
    reference = _thrust_from_diameter(
        7100.0, d_open, prop, rho=1.225, scale=scale
    )

    pretest_config = replace(
        config,
        calibration=replace(
            config.calibration,
            thrust_split_mode="calibrated_effective_diameter_delta",
            tip_delta_calibration_preset="pretest_70_percent_fixed",
        ),
    )
    open_result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=0.0,
        tip_aero_effectiveness=1.0,
        config=pretest_config,
        prop_entry=prop,
    )
    partial_result = compute_split_thrust(
        rpm=7100.0,
        theta_deg=-13.0,
        tip_aero_effectiveness=1.0,
        config=pretest_config,
        prop_entry=prop,
    )
    assert partial_result.thrust_total_n < open_result.thrust_total_n
    assert partial_result.thrust_total_n / reference < 0.70


def test_calibrated_fixed_factor_shared_across_cases(v02_prop) -> None:
    from pythrust.foldable.dynamics.physics_calibrated_thrust_split_diagnostic import (
        run_calibrated_thrust_split_diagnostic,
    )

    config, prop = v02_prop
    rows = run_calibrated_thrust_split_diagnostic(config, prop, t_end_s=0.3)
    pretest_factors = {row.applied_pretest_fixed_factor for row in rows}
    target_factors = {row.applied_target_fixed_factor for row in rows}
    assert len(pretest_factors) == 1
    assert len(target_factors) == 1
    assert rows[0].reference_case_id == "latch_theta0"

    latch = next(row for row in rows if row.case_id == "latch_theta0")
    bias10 = next(row for row in rows if row.case_id == "bias10_k0.25_s5")
    assert latch.T_total_pretest_fixed_n == pytest.approx(
        latch.pretest_required_total_n, rel=1e-4
    )
    assert bias10.T_total_pretest_fixed_n < latch.T_total_pretest_fixed_n
    assert (
        latch.required_pretest_factor_for_this_case
        != bias10.required_pretest_factor_for_this_case
    )


def test_calibrated_efficiency_factor_at_open(v02_prop) -> None:
    config, prop = v02_prop
    d_open = config.geometry.diameter_open_m
    d_root = config.geometry.hinge_position_m * 2.0
    factor = tip_delta_efficiency_factor_for_preset(
        config,
        "pretest_70_percent_fixed",
        rpm=7100.0,
        d_root=d_root,
        d_open=d_open,
        prop_entry=prop,
    )
    assert 0.0 < factor < 1.0


def test_calibrated_diagnostic_csv(v02_prop, tmp_path: Path) -> None:
    from pythrust.foldable.dynamics.physics_calibrated_thrust_split_diagnostic import (
        CALIBRATED_THRUST_SPLIT_DIAGNOSTIC_COLUMNS,
        run_calibrated_thrust_split_diagnostic,
        write_calibrated_thrust_split_diagnostic_csv,
    )

    config, prop = v02_prop
    rows = run_calibrated_thrust_split_diagnostic(config, prop, t_end_s=0.3)
    assert len(rows) == 4
    path = tmp_path / "calibrated_thrust_split_diagnostic.csv"
    write_calibrated_thrust_split_diagnostic_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(CALIBRATED_THRUST_SPLIT_DIAGNOSTIC_COLUMNS)
