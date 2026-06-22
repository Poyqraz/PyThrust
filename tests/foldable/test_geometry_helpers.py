"""Tests for V2 geometry helpers (parallel stow)."""

from __future__ import annotations

import math

import pytest

from pythrust.foldable.geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_m,
    root_diameter_m,
    tip_radial_extension_m,
)
from pythrust.foldable.models import FoldableGeometry, load_config

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
V01_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"

GEOMETRY = FoldableGeometry(
    diameter_open_m=0.25,
    main_blade_length_m=0.10,
    tip_segment_length_m=0.025,
    hinge_position_m=0.10,
    tip_segment_mass_kg=0.002,
    blade_count=2,
    tip_segment_cg_from_hinge_m=0.0125,
    stowed_envelope_diameter_m=0.14,
    stow_model="parallel_fold",
)


def test_parallel_stow_zero_radial_extension() -> None:
    ext = tip_radial_extension_m(-180.0, GEOMETRY, stow_model="parallel_fold")
    assert ext == pytest.approx(0.0, abs=1e-12)


def test_open_full_radial_extension() -> None:
    ext = tip_radial_extension_m(0.0, GEOMETRY, stow_model="parallel_fold")
    assert ext == pytest.approx(0.025)


def test_geometric_diameter_folded_and_open() -> None:
    d_fold = geometric_effective_diameter_m(-180.0, GEOMETRY, stow_model="parallel_fold")
    d_open = geometric_effective_diameter_m(0.0, GEOMETRY, stow_model="parallel_fold")
    assert d_fold == pytest.approx(0.20)
    assert d_open == pytest.approx(0.25)


def test_root_diameter() -> None:
    assert root_diameter_m(GEOMETRY) == pytest.approx(0.20)


def test_aero_diameter_lags_tip_effectiveness() -> None:
    d_geo = geometric_effective_diameter_m(0.0, GEOMETRY, stow_model="parallel_fold")
    d_aero_low = aerodynamic_effective_diameter_m(
        d_geo,
        root_diameter_m=0.20,
        tip_aero_effectiveness=0.0,
    )
    d_aero_full = aerodynamic_effective_diameter_m(
        d_geo,
        root_diameter_m=0.20,
        tip_aero_effectiveness=1.0,
    )
    assert d_aero_low == pytest.approx(0.20)
    assert d_aero_full == pytest.approx(d_geo)


def test_v02_config_loads_parallel_stow() -> None:
    config = load_config(V02_CONFIG)
    assert config.geometry.stow_model == "parallel_fold"
    assert config.hinge.theta_min_deg == pytest.approx(-180.0)
    assert config.hinge.hinge_inertia_kgm2 is not None
    assert config.hinge.hinge_inertia_kgm2 > 0.0


def test_v01_config_keeps_legacy_stow() -> None:
    config = load_config(V01_CONFIG)
    assert config.geometry.stow_model == "legacy_cos"
    assert config.hinge.theta_min_deg == pytest.approx(-45.0)


def test_mid_angle_extension_between_fold_and_open() -> None:
    ext = tip_radial_extension_m(-90.0, GEOMETRY, stow_model="parallel_fold")
    assert 0.0 < ext < GEOMETRY.tip_segment_length_m
    expected = 0.025 * max(0.0, (math.cos(math.radians(-90.0)) + 1.0) / 2.0)
    assert ext == pytest.approx(expected)
