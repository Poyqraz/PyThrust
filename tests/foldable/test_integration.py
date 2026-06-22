"""Integration modülü testleri (V2)."""

import math
from pathlib import Path

import pytest

from pythrust.propellers.database import PropellerDatabase
from pythrust.propulsion.models import OperatingPoint
from pythrust.foldable.integration import (
    FoldableOperatingPointResult,
    evaluate_foldable_operating_point,
    post_process_from_operating_point,
    solve_pythrust_operating_point,
)
from pythrust.foldable.models import load_config
from pythrust.foldable.validation import (
    OPERATING_POINT_COLUMNS,
    validate_operating_point_columns,
    write_operating_point_csv,
)


@pytest.fixture
def project_config():
    return load_config("configs/foldable/TIP_HINGED_250_V01.json")


@pytest.fixture
def prop_entry():
    db = PropellerDatabase()
    db.load(Path("data/propellers/apc_202602"), strict=False)
    entry = db.get("APC_10x4.7SF")
    assert entry is not None
    return entry


def test_post_process_maps_operating_point_fields(project_config) -> None:
    op = OperatingPoint(
        rpm=6000.0,
        advance_ratio=0.0,
        ct=0.1,
        cp=0.05,
        thrust_n=5.0,
        torque_nm=0.12,
        shaft_power_w=75.0,
        motor_power_w=90.0,
        battery_power_w=100.0,
        motor_current_a=8.5,
        motor_voltage_v=10.0,
        is_feasible=True,
        system_efficiency=0.55,
    )

    result = post_process_from_operating_point(
        op,
        project_config,
        throttle=0.8,
        voltage_v=11.1,
    )

    assert result.rpm == 6000.0
    assert result.torque_nm == 0.12
    assert result.current_a == 8.5
    assert result.power_w == 100.0
    assert result.efficiency == 0.55
    assert result.throttle == 0.8
    assert result.voltage_v == 11.1
    assert -45.0 < result.theta_deg < 0.0
    assert 0.0 < result.effective_diameter_m <= 0.25
    assert result.thrust_n > 0.0


def test_post_process_to_dict_has_required_keys(project_config) -> None:
    op = OperatingPoint(
        rpm=8000.0,
        advance_ratio=0.0,
        ct=0.1,
        cp=0.05,
        thrust_n=8.0,
        torque_nm=0.15,
        shaft_power_w=120.0,
        motor_power_w=140.0,
        battery_power_w=150.0,
        motor_current_a=12.0,
        motor_voltage_v=11.0,
        is_feasible=True,
        system_efficiency=0.6,
    )
    result = post_process_from_operating_point(
        op, project_config, throttle=1.0, voltage_v=11.1
    )
    data = result.to_dict()
    for key in OPERATING_POINT_COLUMNS:
        assert key in data


def test_solve_pythrust_operating_point(project_config, prop_entry) -> None:
    op = solve_pythrust_operating_point(project_config, prop_entry, throttle=0.6)
    assert op.rpm > 0.0
    assert op.is_feasible is True


def test_evaluate_foldable_operating_point(project_config, prop_entry) -> None:
    result = evaluate_foldable_operating_point(project_config, prop_entry, throttle=0.6)
    assert isinstance(result, FoldableOperatingPointResult)
    assert result.rpm > 0.0
    assert result.thrust_n >= 0.0
    assert result.is_feasible is True


def test_theta_approaches_zero_at_high_throttle(project_config, prop_entry) -> None:
    low = evaluate_foldable_operating_point(project_config, prop_entry, throttle=0.3)
    high = evaluate_foldable_operating_point(project_config, prop_entry, throttle=0.9)
    assert high.rpm > low.rpm
    assert high.theta_deg > low.theta_deg  # closer to 0 (less negative)


def test_full_open_diameter_at_high_throttle(project_config, prop_entry) -> None:
    result = evaluate_foldable_operating_point(project_config, prop_entry, throttle=1.0)
    if result.rpm >= project_config.hinge.rpm_full_open:
        assert math.isclose(result.theta_deg, 0.0, abs_tol=1e-9)
        assert math.isclose(result.effective_diameter_m, 0.25, rel_tol=1e-6)


def test_operating_point_csv_columns(tmp_path, project_config, prop_entry) -> None:
    result = evaluate_foldable_operating_point(project_config, prop_entry, throttle=0.5)
    output = tmp_path / "op.csv"
    write_operating_point_csv(output, [result])
    assert validate_operating_point_columns(OPERATING_POINT_COLUMNS) == []
    content = output.read_text(encoding="utf-8")
    assert "voltage_v" in content
    assert "model_note" in content
