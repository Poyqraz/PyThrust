"""Reference-scaled thrust model tests."""

import math

import pytest

from pythrust.foldable.models import CalibrationConfig
from pythrust.foldable.performance import (
    THRUST_MODE_REFERENCE_SCALED,
    THRUST_MODE_SIMPLE,
    estimate_foldable_thrust_n,
    estimate_thrust_reference_scaled,
)


@pytest.fixture
def simple_calibration() -> CalibrationConfig:
    return CalibrationConfig(
        k_thrust=1.0,
        k_torque=1.0,
        ct_ref=0.10,
        model_note="test",
        thrust_model_mode=THRUST_MODE_SIMPLE,
    )


@pytest.fixture
def scaled_calibration() -> CalibrationConfig:
    return CalibrationConfig(
        k_thrust=1.0,
        k_torque=1.0,
        ct_ref=0.10,
        model_note="test",
        thrust_model_mode=THRUST_MODE_REFERENCE_SCALED,
        eta_hinge=1.0,
        eta_profile=1.0,
        reference_diameter_m=0.254,
    )


def test_reference_scaled_equals_fixed_when_same_diameter() -> None:
    result = estimate_thrust_reference_scaled(
        fixed_thrust_n=10.0,
        effective_diameter_m=0.254,
        reference_diameter_m=0.254,
        eta_hinge=1.0,
        eta_profile=1.0,
    )
    assert math.isclose(result, 10.0)


def test_reference_scaled_lower_when_smaller_diameter() -> None:
    large = estimate_thrust_reference_scaled(10.0, 0.254, 0.254)
    small = estimate_thrust_reference_scaled(10.0, 0.235, 0.254)
    assert small < large


def test_reference_scaled_mode_requires_fixed_thrust(scaled_calibration) -> None:
    from pythrust.foldable.models import (
        BatteryConfig,
        FoldableGeometry,
        FoldablePropellerConfig,
        HingeConfig,
        KinematicsConfig,
        MotorConfig,
        SystemConfig,
    )

    config = FoldablePropellerConfig(
        id="T",
        description="t",
        geometry=FoldableGeometry(0.25, 0.10, 0.025, 0.10, 0.002),
        hinge=HingeConfig(-45.0, 0.0, 2000.0, 8000.0),
        kinematics=KinematicsConfig("linear_saturation", 1.0),
        calibration=scaled_calibration,
        reference_propeller_id="APC_10x4.7SF",
        motor=MotorConfig(980.0, 0.06, 1.2, 30.0),
        battery=BatteryConfig(11.1, 0.98),
        system=SystemConfig(0.015),
    )

    with pytest.raises(ValueError, match="fixed_thrust_n"):
        estimate_foldable_thrust_n(config, 6000.0, 0.24)

    thrust = estimate_foldable_thrust_n(
        config, 6000.0, 0.24, fixed_thrust_n=8.0, reference_diameter_m=0.254
    )
    assert thrust > 0.0
    assert thrust < 8.0


def test_simple_mode_still_available(simple_calibration) -> None:
    from pythrust.foldable.models import (
        BatteryConfig,
        FoldableGeometry,
        FoldablePropellerConfig,
        HingeConfig,
        KinematicsConfig,
        MotorConfig,
        SystemConfig,
    )

    config = FoldablePropellerConfig(
        id="T",
        description="t",
        geometry=FoldableGeometry(0.25, 0.10, 0.025, 0.10, 0.002),
        hinge=HingeConfig(-45.0, 0.0, 2000.0, 8000.0),
        kinematics=KinematicsConfig("linear_saturation", 1.0),
        calibration=simple_calibration,
        reference_propeller_id="APC_10x4.7SF",
        motor=MotorConfig(980.0, 0.06, 1.2, 30.0),
        battery=BatteryConfig(11.1, 0.98),
        system=SystemConfig(0.015),
    )

    thrust = estimate_foldable_thrust_n(config, 6000.0, 0.25)
    assert thrust > 0.0
