"""Tests for second-order hinge dynamics."""

from __future__ import annotations

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


def test_initial_state_folded(v02_config) -> None:
    state = initial_hinge_state(v02_config)
    assert state.theta_deg == pytest.approx(v02_config.hinge.theta_min_deg)
    assert state.theta_dot_deg_s == pytest.approx(0.0)


def test_hinge_opens_under_centrifugal_load(v02_config) -> None:
    state = initial_hinge_state(v02_config)
    rpm = 7100.0
    for _ in range(500):
        state = integrate_hinge_step(
            state,
            dt_s=0.001,
            rpm=rpm,
            tip_thrust_n=0.0,
            config=v02_config,
        )
    assert state.theta_deg > v02_config.hinge.theta_min_deg + 1.0


def test_second_order_slower_than_quasi_static(v02_config) -> None:
    rpm = 7100.0
    quasi = theta_deg_moment_based(rpm, v02_config)
    state = initial_hinge_state(v02_config)
    for _ in range(200):
        state = integrate_hinge_step(
            state,
            dt_s=0.001,
            rpm=rpm,
            tip_thrust_n=0.0,
            config=v02_config,
        )
    assert state.theta_deg < quasi - 0.5


def test_theta_ddot_populated(v02_config) -> None:
    state = initial_hinge_state(v02_config)
    state = integrate_hinge_step(
        state,
        dt_s=0.001,
        rpm=7100.0,
        tip_thrust_n=0.0,
        config=v02_config,
    )
    assert abs(state.theta_ddot_deg_s2) > 0.0
