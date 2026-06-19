"""Moment kinematics validation tests."""

import math
from pathlib import Path

import pytest

from pythrust.foldable.kinematics import (
    resisting_moment_nm,
    theta_deg_moment_based,
)
from pythrust.foldable.models import HingeConfig, load_config
from pythrust.foldable.moment_validation import (
    MOMENT_KINEMATICS_VALIDATION_COLUMNS,
    VARIANT_PHYSICAL_PARAMETERS_COLUMNS,
    build_moment_kinematics_validation,
    build_variant_physical_parameters,
    write_moment_kinematics_validation_csv,
    write_variant_physical_parameters_csv,
)
from pythrust.propellers.database import PropellerDatabase


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


def test_hinge_radius_does_not_affect_opening_moment(project_config) -> None:
    from dataclasses import replace

    from pythrust.foldable.kinematics import opening_moment_nm

    rpm = 5000.0
    geometry = project_config.geometry
    hinge_a = project_config.hinge
    hinge_b = replace(hinge_a, hinge_radius_m=hinge_a.hinge_radius_m + 0.05)
    m_a = opening_moment_nm(rpm, geometry, hinge_a)
    m_b = opening_moment_nm(rpm, geometry, hinge_b)
    assert m_a == pytest.approx(m_b)


def test_resisting_moment_uses_radians_not_degrees() -> None:
    hinge = HingeConfig(
        theta_min_deg=-45.0,
        theta_max_deg=0.0,
        rpm_threshold=2000.0,
        rpm_full_open=8000.0,
        hinge_stiffness_nm_per_rad=0.55,
        hinge_friction_nm=0.007,
    )
    at_min = resisting_moment_nm(-45.0, hinge)
    assert at_min == pytest.approx(0.007)

    at_zero = resisting_moment_nm(0.0, hinge)
    expected_rad = 0.55 * math.radians(45.0) + 0.007
    expected_deg_bug = 0.55 * 45.0 + 0.007
    assert at_zero == pytest.approx(expected_rad)
    assert at_zero != pytest.approx(expected_deg_bug)


def test_theta_solution_matches_radian_stiffness(project_config) -> None:
    from pythrust.foldable.kinematics import opening_moment_nm

    rpm = 2500.0
    hinge = project_config.hinge
    geometry = project_config.geometry
    m_open = opening_moment_nm(rpm, geometry, hinge)
    theta = theta_deg_moment_based(rpm, project_config)
    m_resist = resisting_moment_nm(theta, hinge)
    assert hinge.theta_min_deg < theta < hinge.theta_max_deg
    assert m_open == pytest.approx(m_resist, rel=1e-9)


def test_validation_csv_columns(project_config, prop_entry, tmp_path) -> None:
    rows = build_moment_kinematics_validation(
        project_config,
        prop_entry,
        throttle_values=[0.4],
    )
    output = tmp_path / "moment_kinematics_validation.csv"
    write_moment_kinematics_validation_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in MOMENT_KINEMATICS_VALIDATION_COLUMNS:
        assert col in content
    assert len(rows) == 5


def test_variant_physical_parameters_csv(project_config, tmp_path) -> None:
    rows = build_variant_physical_parameters(project_config)
    output = tmp_path / "variant_physical_parameters.csv"
    write_variant_physical_parameters_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in VARIANT_PHYSICAL_PARAMETERS_COLUMNS:
        assert col in content
    assert len(rows) == 5
    assert all(row.tip_length_m > 0.0 for row in rows)
