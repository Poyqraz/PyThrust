"""Kinematics modülü testleri."""

import math

import pytest

from pythrust.foldable.kinematics import theta_deg_from_hinge, theta_deg_from_rpm
from pythrust.foldable.models import (
    CalibrationConfig,
    FoldableGeometry,
    FoldablePropellerConfig,
    HingeConfig,
    KinematicsConfig,
    MotorConfig,
    BatteryConfig,
    SystemConfig,
    load_config,
)


@pytest.fixture
def sample_config() -> FoldablePropellerConfig:
    return FoldablePropellerConfig(
        id="TEST",
        description="test",
        geometry=FoldableGeometry(
            diameter_open_m=0.25,
            main_blade_length_m=0.10,
            tip_segment_length_m=0.025,
            hinge_position_m=0.10,
            tip_segment_mass_kg=0.002,
        ),
        hinge=HingeConfig(
            theta_min_deg=-45.0,
            theta_max_deg=0.0,
            rpm_threshold=2000.0,
            rpm_full_open=8000.0,
        ),
        kinematics=KinematicsConfig(model="linear_saturation", k_open=1.0),
        calibration=CalibrationConfig(
            k_thrust=1.0,
            k_torque=1.0,
            ct_ref=0.10,
            model_note="test",
        ),
        reference_propeller_id="APC_10x4.7",
        motor=MotorConfig(980.0, 0.06, 1.2, 30.0),
        battery=BatteryConfig(11.1, 0.98),
        system=SystemConfig(0.015),
    )


def test_theta_below_threshold_is_fully_folded(sample_config: FoldablePropellerConfig) -> None:
    assert theta_deg_from_rpm(1000.0, sample_config) == -45.0


def test_theta_at_full_open_is_zero(sample_config: FoldablePropellerConfig) -> None:
    assert theta_deg_from_rpm(8000.0, sample_config) == 0.0
    assert theta_deg_from_rpm(10000.0, sample_config) == 0.0


def test_theta_increases_toward_open_as_rpm_increases(sample_config: FoldablePropellerConfig) -> None:
    """RPM arttıkça açı tam açık duruma (0°) yaklaşmalı."""
    angles = [theta_deg_from_rpm(rpm, sample_config) for rpm in [2500.0, 4000.0, 6000.0, 7500.0]]
    assert all(angles[i] < angles[i + 1] for i in range(len(angles) - 1))
    assert angles[-1] > angles[0]
    assert angles[-1] <= 0.0


def test_theta_midpoint_is_halfway(sample_config: FoldablePropellerConfig) -> None:
    mid_rpm = 5000.0  # halfway between 2000 and 8000
    expected = -22.5
    assert math.isclose(theta_deg_from_rpm(mid_rpm, sample_config), expected, abs_tol=1e-9)


def test_load_config_from_json() -> None:
    config = load_config("configs/foldable/TIP_HINGED_250_V01.json")
    assert config.id == "TIP_HINGED_250_V01"
    assert config.geometry.diameter_open_m == 0.25
