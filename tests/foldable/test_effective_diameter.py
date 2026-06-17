"""Effective diameter modülü testleri."""

import math

import pytest

from pythrust.foldable.effective_diameter import (
    effective_diameter_from_geometry,
    effective_diameter_m,
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
)


@pytest.fixture
def geometry() -> FoldableGeometry:
    return FoldableGeometry(
        diameter_open_m=0.25,
        main_blade_length_m=0.10,
        tip_segment_length_m=0.025,
        hinge_position_m=0.10,
        tip_segment_mass_kg=0.002,
    )


@pytest.fixture
def sample_config(geometry: FoldableGeometry) -> FoldablePropellerConfig:
    return FoldablePropellerConfig(
        id="TEST",
        description="test",
        geometry=geometry,
        hinge=HingeConfig(-45.0, 0.0, 2000.0, 8000.0),
        kinematics=KinematicsConfig("linear_saturation", 1.0),
        calibration=CalibrationConfig(1.0, 1.0, 0.10, "test"),
        reference_propeller_id="APC_10x4.7",
        motor=MotorConfig(980.0, 0.06, 1.2, 30.0),
        battery=BatteryConfig(11.1, 0.98),
        system=SystemConfig(0.015),
    )


def test_fully_open_diameter_equals_open_diameter(geometry: FoldableGeometry) -> None:
    """Tam açık durumda efektif çap açık çapa eşit olmalı."""
    d_eff = effective_diameter_from_geometry(0.0, geometry)
    assert math.isclose(d_eff, 0.25, rel_tol=1e-9)


def test_folded_diameter_is_smaller_than_open(geometry: FoldableGeometry) -> None:
    """Katlı durumda efektif çap daha küçük olmalı."""
    d_open = effective_diameter_from_geometry(0.0, geometry)
    d_folded = effective_diameter_from_geometry(-45.0, geometry)
    assert d_folded < d_open


def test_diameter_increases_as_angle_opens(geometry: FoldableGeometry) -> None:
    diameters = [
        effective_diameter_from_geometry(angle, geometry)
        for angle in [-45.0, -30.0, -15.0, 0.0]
    ]
    assert all(diameters[i] < diameters[i + 1] for i in range(len(diameters) - 1))


def test_config_wrapper(sample_config: FoldablePropellerConfig) -> None:
    assert math.isclose(effective_diameter_m(0.0, sample_config), 0.25, rel_tol=1e-9)
