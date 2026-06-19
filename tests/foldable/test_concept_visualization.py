"""Tests for concept/report foldable propeller visualization."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from pythrust.foldable.visualization.concept.geometry import (
    main_blade_polygon,
    secondary_blade_polygon,
    static_reference_state,
    tip_point,
)
from pythrust.foldable.visualization.concept.panels import (
    draw_throttle_sweep_concept,
    draw_variant_compare_concept,
)
from pythrust.foldable.visualization.concept.schematic import (
    draw_single_state_concept,
    draw_static_overview,
)
from pythrust.foldable.visualization.io import join_visual_states
from pythrust.foldable.visualization.state import PropellerVisualState

CONCEPT_OUTPUT_NAMES = (
    "concept_static_overview.png",
    "concept_state_TIP_HINGED_250_RT75_25_thr_0.6.png",
    "concept_throttle_sweep_TIP_HINGED_250_RT75_25.png",
    "concept_variant_compare_thr_0.6.png",
)


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


def test_main_blade_polygon_has_four_vertices() -> None:
    state = static_reference_state()
    polygon = main_blade_polygon(state)
    assert len(polygon) == 4


def test_secondary_blade_open_tip_reaches_open_radius() -> None:
    state = static_reference_state()
    tip_x, tip_y = tip_point(state)
    assert tip_x == pytest.approx(0.125)
    assert tip_y == pytest.approx(0.0)


def test_secondary_blade_folded_tip_y_is_negative() -> None:
    state = _rt75_state(theta_deg=-45.0, effective_diameter_m=0.235)
    _, tip_y = tip_point(state)
    assert tip_y < 0.0


def test_secondary_polygon_follows_theta() -> None:
    state = _rt75_state(theta_deg=-30.0, effective_diameter_m=0.24)
    polygon = secondary_blade_polygon(state)
    centroid_x = sum(point[0] for point in polygon) / len(polygon)
    centroid_y = sum(point[1] for point in polygon) / len(polygon)
    tip_x, tip_y = tip_point(state)
    mid_x = (state.hinge_position_m + tip_x) / 2.0
    mid_y = tip_y / 2.0
    assert centroid_x == pytest.approx(mid_x, rel=0.05)
    assert math.copysign(1.0, centroid_y) == math.copysign(1.0, mid_y)


def test_draw_static_overview_writes_png(tmp_path: Path) -> None:
    output = tmp_path / "concept_static_overview.png"
    draw_static_overview(output_path=output)
    assert output.is_file()
    assert output.stat().st_size > 0


def test_draw_single_state_concept_writes_png(tmp_path: Path) -> None:
    state = _rt75_state(theta_deg=-10.0, effective_diameter_m=0.249)
    output = tmp_path / "concept_state.png"
    draw_single_state_concept(state, output_path=output)
    assert output.is_file()
    assert output.stat().st_size > 0


def test_concept_panels_write_pngs(tmp_path: Path) -> None:
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
    sweep_png = draw_throttle_sweep_concept(
        "TIP_HINGED_250_RT75_25",
        states,
        output_path=tmp_path / "concept_throttle_sweep.png",
    )
    compare_png = draw_variant_compare_concept(
        0.6,
        states,
        output_path=tmp_path / "concept_variant_compare.png",
    )
    assert sweep_png.stat().st_size > 0
    assert compare_png.stat().st_size > 0


def test_concept_output_filenames_are_stable() -> None:
    assert CONCEPT_OUTPUT_NAMES == (
        "concept_static_overview.png",
        "concept_state_TIP_HINGED_250_RT75_25_thr_0.6.png",
        "concept_throttle_sweep_TIP_HINGED_250_RT75_25.png",
        "concept_variant_compare_thr_0.6.png",
    )
