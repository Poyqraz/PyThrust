"""Kinematics modülü testleri."""

import math
from dataclasses import replace

import pytest

from pythrust.foldable.kinematics import (
    opening_moment_nm,
    theta_deg_from_hinge,
    theta_deg_from_rpm,
    theta_deg_moment_based,
)
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
from pythrust.foldable.variants import make_variant_config


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
            tip_segment_cg_from_hinge_m=0.0125,
        ),
        hinge=HingeConfig(
            theta_min_deg=-45.0,
            theta_max_deg=0.0,
            rpm_threshold=2000.0,
            rpm_full_open=8000.0,
            hinge_radius_m=0.10,
            hinge_stiffness_nm_per_rad=0.55,
            hinge_friction_nm=0.007,
        ),
        kinematics=KinematicsConfig(
            model="linear_saturation",
            k_open=1.0,
            kinematics_mode="rpm_only",
        ),
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


@pytest.fixture
def moment_config(sample_config: FoldablePropellerConfig) -> FoldablePropellerConfig:
    return replace(
        sample_config,
        kinematics=KinematicsConfig(
            model="linear_saturation",
            k_open=1.0,
            kinematics_mode="moment_based",
        ),
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
    assert config.geometry.tip_segment_cg_from_hinge_m == pytest.approx(0.0125)
    assert config.kinematics.kinematics_mode == "moment_based"
    assert config.hinge.hinge_stiffness_nm_per_rad == pytest.approx(0.55)


def test_moment_based_zero_rpm_is_folded(moment_config: FoldablePropellerConfig) -> None:
    assert theta_deg_moment_based(0.0, moment_config) == -45.0
    assert theta_deg_from_rpm(0.0, moment_config) == -45.0


def test_moment_based_high_rpm_approaches_open(moment_config: FoldablePropellerConfig) -> None:
    assert theta_deg_moment_based(9000.0, moment_config) == 0.0


def test_moment_based_monotonic_with_rpm(moment_config: FoldablePropellerConfig) -> None:
    rpms = [1500.0, 3000.0, 5000.0, 7000.0, 8500.0]
    angles = [theta_deg_moment_based(rpm, moment_config) for rpm in rpms]
    assert all(angles[i] <= angles[i + 1] for i in range(len(angles) - 1))


def test_moment_based_geometry_changes_theta_at_same_rpm(
    moment_config: FoldablePropellerConfig,
) -> None:
    short_tip = replace(
        moment_config.geometry,
        tip_segment_length_m=0.015,
        tip_segment_cg_from_hinge_m=0.0075,
        tip_segment_mass_kg=0.0012,
    )
    long_tip = replace(
        moment_config.geometry,
        tip_segment_length_m=0.035,
        tip_segment_cg_from_hinge_m=0.0175,
        tip_segment_mass_kg=0.0028,
    )
    rpm = 5000.0
    theta_short = theta_deg_moment_based(
        rpm,
        replace(moment_config, geometry=short_tip),
    )
    theta_long = theta_deg_moment_based(
        rpm,
        replace(moment_config, geometry=long_tip),
    )
    assert theta_long > theta_short
    assert opening_moment_nm(rpm, long_tip, moment_config.hinge) > opening_moment_nm(
        rpm,
        short_tip,
        moment_config.hinge,
    )


def test_variant_configs_produce_different_theta_at_same_rpm(
    moment_config: FoldablePropellerConfig,
) -> None:
    short_variant = make_variant_config(moment_config, 85, 15)
    long_variant = make_variant_config(moment_config, 65, 35)
    rpm = 4500.0
    theta_short = theta_deg_from_rpm(rpm, short_variant)
    theta_long = theta_deg_from_rpm(rpm, long_variant)
    assert theta_long > theta_short


def test_moment_based_invalid_stiffness_raises(moment_config: FoldablePropellerConfig) -> None:
    bad_hinge = replace(moment_config.hinge, hinge_stiffness_nm_per_rad=0.0)
    bad_config = replace(moment_config, hinge=bad_hinge)
    with pytest.raises(ValueError, match="hinge_stiffness_nm_per_rad"):
        theta_deg_moment_based(3000.0, bad_config)


def test_theta_deg_from_hinge_unchanged_for_rpm_only() -> None:
    hinge = HingeConfig(-45.0, 0.0, 2000.0, 8000.0)
    kinematics = KinematicsConfig("linear_saturation", 1.0, "rpm_only")
    assert theta_deg_from_hinge(5000.0, hinge, kinematics) == -22.5
