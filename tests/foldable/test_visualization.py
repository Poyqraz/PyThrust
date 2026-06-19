"""Tests for foldable 2D visualization geometry and I/O."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from pythrust.foldable.effective_diameter import effective_diameter_from_geometry
from pythrust.foldable.models import FoldableGeometry
from pythrust.foldable.visualization.geometry_2d import (
    annotation_lines,
    blade_polylines,
    effective_radius_circle,
)
from pythrust.foldable.visualization.io import join_visual_states
from pythrust.foldable.visualization.panels import (
    draw_throttle_sweep_panel,
    draw_variant_compare_panel,
)
from pythrust.foldable.visualization.schematic import draw_single_state
from pythrust.foldable.visualization.state import PropellerVisualState


def _rt75_state(*, theta_deg: float, effective_diameter_m: float) -> PropellerVisualState:
    return PropellerVisualState(
        variant_id="TIP_HINGED_250_RT75_25",
        root_ratio=75,
        tip_ratio=25,
        throttle=0.6,
        rpm=5697.0,
        theta_deg=theta_deg,
        effective_diameter_m=effective_diameter_m,
        opening_moment_nm=0.43,
        resisting_moment_nm=0.43,
        moment_margin_nm=0.0,
        hinge_state="opening",
        foldable_thrust_n=5.8,
        hinge_position_m=0.09375,
        tip_segment_length_m=0.03125,
    )


def test_blade_polyline_open_tip_reaches_open_radius() -> None:
    state = _rt75_state(theta_deg=0.0, effective_diameter_m=0.25)
    polylines = blade_polylines(state)
    tip = polylines[0][-1]
    assert tip[0] == pytest.approx(0.125)
    assert tip[1] == pytest.approx(0.0)
    assert len(polylines) == 2


def test_blade_polyline_folded_matches_effective_radius() -> None:
    geometry = FoldableGeometry(
        diameter_open_m=0.25,
        main_blade_length_m=0.09375,
        tip_segment_length_m=0.03125,
        hinge_position_m=0.09375,
        tip_segment_mass_kg=0.0025,
        tip_segment_cg_from_hinge_m=0.015625,
    )
    theta_min = -45.0
    d_eff = effective_diameter_from_geometry(theta_min, geometry)
    state = _rt75_state(theta_deg=theta_min, effective_diameter_m=d_eff)
    tip = blade_polylines(state)[0][-1]
    assert tip[0] == pytest.approx(d_eff / 2.0, rel=1e-6)


def test_effective_radius_circle() -> None:
    state = _rt75_state(theta_deg=-10.0, effective_diameter_m=0.24)
    cx, cy, radius = effective_radius_circle(state)
    assert (cx, cy) == (0.0, 0.0)
    assert radius == pytest.approx(0.12)


def test_annotation_lines_include_key_fields() -> None:
    state = _rt75_state(theta_deg=-5.0, effective_diameter_m=0.249)
    text = "\n".join(annotation_lines(state))
    assert "TIP_HINGED_250_RT75_25" in text
    assert "hinge:" in text
    assert "T_fold:" in text


def test_join_visual_states_from_project_csvs() -> None:
    sweep = Path("outputs/foldable/design_variant_sweep.csv")
    moment = Path("outputs/foldable/moment_kinematics_validation.csv")
    params = Path("outputs/foldable/variant_physical_parameters.csv")
    if not (sweep.is_file() and moment.is_file() and params.is_file()):
        pytest.skip("foldable CSV outputs not generated")

    states = join_visual_states(sweep, moment, params, throttle_values=[0.6])
    assert len(states) == 5
    rt75 = next(s for s in states if s.variant_id == "TIP_HINGED_250_RT75_25")
    assert rt75.foldable_thrust_n > 0.0
    assert rt75.opening_moment_nm >= 0.0


def test_join_includes_synthesized_throttle_zero(tmp_path) -> None:
    sweep_path = tmp_path / "sweep.csv"
    moment_path = tmp_path / "moment.csv"
    params_path = tmp_path / "params.csv"

    sweep_path.write_text(
        "variant_id,root_ratio,tip_ratio,voltage_v,throttle,rpm,theta_deg,"
        "effective_diameter_m,fixed_thrust_n,foldable_thrust_n,"
        "thrust_difference_percent,compactness_ratio,model_note\n"
        "TIP_HINGED_250_RT75_25,75,25,11.1,0.6,5000,-5,0.24,6,5.5,-8,0.94,note\n",
        encoding="utf-8",
    )
    moment_path.write_text(
        "variant_id,throttle,rpm,theta_deg,effective_diameter_m,opening_moment_nm,"
        "resisting_moment_nm,moment_margin_nm,hinge_state\n"
        "TIP_HINGED_250_RT75_25,0.6,5000,-5,0.24,0.2,0.2,0,opening\n",
        encoding="utf-8",
    )
    params_path.write_text(
        "variant_id,root_ratio,tip_ratio,tip_length_m,tip_mass_kg,"
        "tip_segment_cg_from_hinge_m,hinge_radius_m,hinge_stiffness_nm_per_rad,hinge_friction_nm\n"
        "TIP_HINGED_250_RT75_25,75,25,0.03125,0.0025,0.015625,0.09375,0.55,0.007\n",
        encoding="utf-8",
    )

    states = join_visual_states(
        sweep_path,
        moment_path,
        params_path,
        throttle_values=[0.0, 0.6],
    )
    zero = next(s for s in states if abs(s.throttle) < 1e-9)
    assert zero.rpm == 0.0
    assert zero.theta_deg == pytest.approx(-45.0)
    assert zero.foldable_thrust_n == 0.0
    assert zero.hinge_state == "folded"


def test_draw_single_state_writes_png(tmp_path) -> None:
    state = _rt75_state(theta_deg=-20.0, effective_diameter_m=0.245)
    output = tmp_path / "single.png"
    draw_single_state(state, output_path=output)
    assert output.is_file()
    assert output.stat().st_size > 0


def test_draw_panels_write_pngs(tmp_path) -> None:
    sweep = Path("outputs/foldable/design_variant_sweep.csv")
    moment = Path("outputs/foldable/moment_kinematics_validation.csv")
    params = Path("outputs/foldable/variant_physical_parameters.csv")
    if not (sweep.is_file() and moment.is_file() and params.is_file()):
        pytest.skip("foldable CSV outputs not generated")

    states = join_visual_states(
        sweep,
        moment,
        params,
        throttle_values=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    )
    sweep_png = draw_throttle_sweep_panel(
        "TIP_HINGED_250_RT75_25",
        states,
        output_path=tmp_path / "sweep.png",
    )
    compare_png = draw_variant_compare_panel(
        0.6,
        states,
        output_path=tmp_path / "compare.png",
    )
    assert sweep_png.stat().st_size > 0
    assert compare_png.stat().st_size > 0
