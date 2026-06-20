"""Tests for second-order hinge dynamics."""

from __future__ import annotations

from dataclasses import replace

import pytest

from pythrust.foldable.dynamics.hinge_dynamics import (
    HingeState,
    initial_hinge_state,
    integrate_hinge_step,
)
from pythrust.foldable.kinematics import theta_deg_moment_based
from pythrust.foldable.models import load_config

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"


@pytest.fixture(scope="module")
def v02_config():
    return load_config(V02_CONFIG)


@pytest.fixture(scope="module")
def progress_lever_config(v02_config):
    return replace(
        v02_config,
        hinge=replace(v02_config.hinge, cent_moment_model="progress_lever"),
    )


def test_initial_state_folded(v02_config) -> None:
    state = initial_hinge_state(v02_config)
    assert state.theta_deg == pytest.approx(v02_config.hinge.theta_min_deg)
    assert state.theta_dot_deg_s == pytest.approx(0.0)


def test_hinge_opens_under_centrifugal_load(progress_lever_config) -> None:
    state = initial_hinge_state(progress_lever_config)
    rpm = 7100.0
    for _ in range(500):
        state = integrate_hinge_step(
            state,
            dt_s=0.001,
            rpm=rpm,
            tip_thrust_n=0.0,
            config=progress_lever_config,
        )
    assert state.theta_deg > progress_lever_config.hinge.theta_min_deg + 1.0


def test_second_order_slower_than_quasi_static(progress_lever_config) -> None:
    rpm = 7100.0
    quasi = theta_deg_moment_based(rpm, progress_lever_config)
    state = initial_hinge_state(progress_lever_config)
    for _ in range(200):
        state = integrate_hinge_step(
            state,
            dt_s=0.001,
            rpm=rpm,
            tip_thrust_n=0.0,
            config=progress_lever_config,
        )
    assert state.theta_deg < quasi - 0.5


def test_theta_ddot_populated(progress_lever_config) -> None:
    state = initial_hinge_state(progress_lever_config)
    state = integrate_hinge_step(
        state,
        dt_s=0.001,
        rpm=7100.0,
        tip_thrust_n=0.0,
        config=progress_lever_config,
    )
    assert abs(state.theta_ddot_deg_s2) > 0.0


def test_geometric_perfect_fold_stays_folded(v02_config) -> None:
    state = initial_hinge_state(v02_config)
    for _ in range(500):
        state = integrate_hinge_step(
            state,
            dt_s=0.001,
            rpm=7100.0,
            tip_thrust_n=0.0,
            config=v02_config,
        )
    assert state.theta_deg == pytest.approx(v02_config.hinge.theta_min_deg, abs=0.5)
    assert state.theta_dot_deg_s == pytest.approx(0.0, abs=1.0)

