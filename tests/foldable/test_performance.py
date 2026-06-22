"""Performance modülü testleri."""

import math

import pytest

from pythrust.foldable.models import (
    CalibrationConfig,
    FoldableGeometry,
    FoldablePropellerConfig,
    HingeConfig,
    KinematicsConfig,
    MotorConfig,
    BatteryConfig,
    SystemConfig,
)
from pythrust.foldable.performance import estimate_thrust_n, evaluate_sweep_row


@pytest.fixture
def sample_config() -> FoldablePropellerConfig:
    return FoldablePropellerConfig(
        id="TEST",
        description="test",
        geometry=FoldableGeometry(0.25, 0.10, 0.025, 0.10, 0.002),
        hinge=HingeConfig(-45.0, 0.0, 2000.0, 8000.0),
        kinematics=KinematicsConfig("linear_saturation", 1.0),
        calibration=CalibrationConfig(1.0, 1.0, 0.10, "V1 test"),
        reference_propeller_id="APC_10x4.7",
        motor=MotorConfig(980.0, 0.06, 1.2, 30.0),
        battery=BatteryConfig(11.1, 0.98),
        system=SystemConfig(0.015),
    )


def test_thrust_zero_at_zero_rpm() -> None:
    assert estimate_thrust_n(0.0, 0.25) == 0.0


def test_thrust_increases_with_rpm() -> None:
    t_low = estimate_thrust_n(4000.0, 0.25, ct_ref=0.10, k_thrust=1.0)
    t_high = estimate_thrust_n(8000.0, 0.25, ct_ref=0.10, k_thrust=1.0)
    assert t_high > t_low > 0.0


def test_thrust_scales_with_diameter() -> None:
    t_small = estimate_thrust_n(6000.0, 0.20, ct_ref=0.10)
    t_large = estimate_thrust_n(6000.0, 0.25, ct_ref=0.10)
    assert t_large > t_small


def test_evaluate_sweep_row_fields(sample_config: FoldablePropellerConfig) -> None:
    row = evaluate_sweep_row(6000.0, sample_config)
    assert row.rpm == 6000.0
    assert -45.0 < row.theta_deg < 0.0
    assert 0.0 < row.effective_diameter_m <= 0.25
    assert row.thrust_n > 0.0
    assert row.model_note == "V1 test"


def test_thrust_formula_reference() -> None:
    rpm = 6000.0
    d = 0.25
    n = rpm / 60.0
    expected = 0.10 * 1.225 * (n ** 2) * (d ** 4)
    assert math.isclose(estimate_thrust_n(rpm, d, ct_ref=0.10, k_thrust=1.0), expected, rel_tol=1e-9)
