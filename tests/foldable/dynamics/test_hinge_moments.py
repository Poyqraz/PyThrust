"""Tests for hinge moment components."""

from __future__ import annotations

import pytest

from pythrust.foldable.dynamics.hinge_moments import (
    HingeMomentComponents,
    compute_hinge_moments,
    coulomb_friction_moment_nm,
    stiffness_moment_nm,
)
from pythrust.foldable.models import load_config

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"


@pytest.fixture(scope="module")
def v02_config():
    return load_config(V02_CONFIG)


def test_stiffness_zero_at_theta_min(v02_config) -> None:
    m = stiffness_moment_nm(v02_config.hinge.theta_min_deg, v02_config)
    assert m == pytest.approx(0.0, abs=1e-12)


def test_friction_opposes_positive_motion(v02_config) -> None:
    m = coulomb_friction_moment_nm(1.0, 0.5, v02_config)
    assert m > 0.0


def test_compute_hinge_moments_has_all_fields(v02_config) -> None:
    result = compute_hinge_moments(
        rpm=7100.0,
        theta_deg=-90.0,
        theta_dot_rad_s=0.1,
        tip_thrust_n=0.5,
        config=v02_config,
    )
    assert isinstance(result, HingeMomentComponents)
    assert result.M_centrifugal_nm >= 0.0
    assert result.M_net_nm == pytest.approx(
        result.M_centrifugal_nm
        + result.M_aero_nm
        - result.M_stiffness_nm
        - result.M_damping_nm
        - result.M_friction_nm
        - result.M_stop_nm
    )


def test_centrifugal_zero_at_zero_rpm(v02_config) -> None:
    result = compute_hinge_moments(
        rpm=0.0,
        theta_deg=-90.0,
        theta_dot_rad_s=0.0,
        tip_thrust_n=0.0,
        config=v02_config,
    )
    assert result.M_centrifugal_nm == pytest.approx(0.0)
