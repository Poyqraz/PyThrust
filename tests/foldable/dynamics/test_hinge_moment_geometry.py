"""Tests for explicit hinge moment geometry models."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from pythrust.foldable.dynamics.hinge_moment_geometry import (
    centrifugal_moment_nm_for_model,
    initial_theta_deg,
    progress_lever_arm_m,
)
from pythrust.foldable.models import load_config

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"


@pytest.fixture(scope="module")
def v02_config():
    return load_config(V02_CONFIG)


def test_geometric_moment_zero_at_open_and_folded(v02_config) -> None:
    rpm = 7100.0
    cfg = replace(v02_config, hinge=replace(v02_config.hinge, cent_moment_model="geometric_radial"))
    m_open = centrifugal_moment_nm_for_model(rpm, 0.0, cfg)
    m_fold = centrifugal_moment_nm_for_model(rpm, -180.0, cfg)
    assert m_open == pytest.approx(0.0, abs=1e-9)
    assert m_fold == pytest.approx(0.0, abs=1e-6)


def test_geometric_moment_max_near_mid_sweep(v02_config) -> None:
    rpm = 7100.0
    cfg = replace(v02_config, hinge=replace(v02_config.hinge, cent_moment_model="geometric_radial"))
    m_90 = centrifugal_moment_nm_for_model(rpm, -90.0, cfg)
    m_150 = centrifugal_moment_nm_for_model(rpm, -150.0, cfg)
    assert m_90 > m_150


def test_deployment_bias_creates_folded_opening_moment(v02_config) -> None:
    rpm = 7100.0
    cfg = replace(
        v02_config,
        hinge=replace(
            v02_config.hinge,
            cent_moment_model="geometric_radial",
            deployment_bias_angle_deg=10.0,
        ),
    )
    m = centrifugal_moment_nm_for_model(rpm, -180.0, cfg)
    assert m > 0.0


def test_progress_lever_decreases_toward_open(v02_config) -> None:
    cfg = replace(v02_config, hinge=replace(v02_config.hinge, cent_moment_model="progress_lever"))
    lever_fold = progress_lever_arm_m(-180.0, cfg)
    lever_mid = progress_lever_arm_m(-90.0, cfg)
    lever_open = progress_lever_arm_m(0.0, cfg)
    assert lever_fold > lever_mid > lever_open
    assert lever_open == pytest.approx(0.0)


def test_initial_stow_offset(v02_config) -> None:
    cfg = replace(
        v02_config,
        hinge=replace(v02_config.hinge, initial_stow_offset_deg=15.0),
    )
    assert initial_theta_deg(cfg) == pytest.approx(-165.0)


def test_classify_physics_hinge_states() -> None:
    from pythrust.foldable.kinematics import classify_physics_hinge_state
    from pythrust.foldable.models import HingeConfig

    hinge = HingeConfig(
        theta_min_deg=-180.0,
        theta_max_deg=0.0,
        rpm_threshold=2000.0,
        rpm_full_open=8000.0,
    )
    assert (
        classify_physics_hinge_state(
            7100.0, 0.0, 0.0, 0.0, 0.1, hinge
        )
        == "open_stop"
    )
    assert (
        classify_physics_hinge_state(
            7100.0, -60.0, 0.0, 0.5, 0.4, hinge
        )
        == "equilibrium_partial"
    )
    assert (
        classify_physics_hinge_state(
            7100.0, -120.0, 50.0, 0.5, 0.1, hinge
        )
        == "opening"
    )
