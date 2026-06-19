"""Tests for concept/report foldable propeller visualization."""

from __future__ import annotations

from pathlib import Path

import pytest

from pythrust.foldable.visualization.concept.deployment_mapping import (
    deployment_progress_from_theta,
    display_hinge_angle_from_progress,
    frame_from_state,
    frame_folded_reference,
)
from pythrust.foldable.visualization.concept.geometry import (
    display_tip_point,
    main_blade_polygon,
    secondary_blade_polygon,
    static_folded_frame,
)
from pythrust.foldable.visualization.concept.panels import (
    draw_throttle_sweep_concept,
    draw_variant_compare_concept,
)
from pythrust.foldable.visualization.concept.schematic import (
    draw_single_state_concept,
    draw_static_overview,
)
from pythrust.foldable.visualization.concept.style import (
    CONCEPT_FOLDED_DISPLAY_ANGLE_DEG,
    CONCEPT_OPEN_DISPLAY_ANGLE_DEG,
)
from pythrust.foldable.visualization.io import join_visual_states
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
        theta_min_deg=-45.0,
    )


def test_folded_progress_maps_to_display_angle_180() -> None:
    progress = deployment_progress_from_theta(-45.0, theta_min_deg=-45.0)
    assert progress == pytest.approx(0.0)
    assert display_hinge_angle_from_progress(progress) == pytest.approx(
        CONCEPT_FOLDED_DISPLAY_ANGLE_DEG
    )


def test_open_progress_maps_to_display_angle_0() -> None:
    progress = deployment_progress_from_theta(0.0, theta_min_deg=-45.0)
    assert progress == pytest.approx(1.0)
    assert display_hinge_angle_from_progress(progress) == pytest.approx(
        CONCEPT_OPEN_DISPLAY_ANGLE_DEG
    )


def test_folded_display_tip_points_toward_hub() -> None:
    frame = frame_folded_reference()
    tip_x, tip_y = display_tip_point(frame)
    assert tip_x < frame.hinge_position_m
    assert tip_y == pytest.approx(0.0, abs=1e-9)


def test_open_display_tip_reaches_radial_extension() -> None:
    state = _rt75_state(theta_deg=0.0, effective_diameter_m=0.25)
    frame = frame_from_state(state)
    tip_x, tip_y = display_tip_point(frame)
    assert tip_x == pytest.approx(0.125)
    assert tip_y == pytest.approx(0.0)


def test_static_folded_frame_is_fully_folded() -> None:
    frame = static_folded_frame()
    assert frame.deployment_progress_01 == pytest.approx(0.0)
    assert frame.display_hinge_angle_deg == pytest.approx(180.0)


def test_main_blade_polygon_has_four_vertices() -> None:
    frame = static_folded_frame()
    assert len(main_blade_polygon(frame)) == 4


def test_secondary_blade_polygon_has_four_vertices() -> None:
    frame = static_folded_frame()
    assert len(secondary_blade_polygon(frame)) == 4


def test_partial_deployment_tip_between_folded_and_open() -> None:
    state = _rt75_state(theta_deg=-22.5, effective_diameter_m=0.24)
    frame = frame_from_state(state)
    tip_x, _ = display_tip_point(frame)
    folded_x, _ = display_tip_point(frame_folded_reference())
    open_state = _rt75_state(theta_deg=0.0, effective_diameter_m=0.25)
    open_x, _ = display_tip_point(frame_from_state(open_state))
    assert folded_x < tip_x < open_x


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
