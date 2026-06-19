"""Tests for concept deployment mapping (visualization-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pythrust.foldable.visualization.concept.deployment_mapping import (
    deployment_progress_from_theta,
    display_hinge_angle_from_progress,
    frame_at_progress,
    frame_folded_reference,
    frame_from_state,
    pseudo_time_from_progress,
)
from pythrust.foldable.visualization.concept.deployment_geometry import display_tip_point
from pythrust.foldable.visualization.concept.frames import export_deployment_frames
from pythrust.foldable.visualization.concept.sequence import draw_deployment_sequence
from pythrust.foldable.visualization.concept.style import (
    CONCEPT_FOLDED_DISPLAY_ANGLE_DEG,
    CONCEPT_OPEN_DISPLAY_ANGLE_DEG,
    DEPLOYMENT_SEQUENCE_DURATION_S,
)
from pythrust.foldable.visualization.state import PropellerVisualState


def _rt75_state(*, theta_deg: float) -> PropellerVisualState:
    return PropellerVisualState(
        variant_id="TIP_HINGED_250_RT75_25",
        root_ratio=75,
        tip_ratio=25,
        throttle=0.6,
        rpm=5697.0,
        theta_deg=theta_deg,
        effective_diameter_m=0.25,
        opening_moment_nm=0.43,
        resisting_moment_nm=0.43,
        moment_margin_nm=0.0,
        hinge_state="opening",
        foldable_thrust_n=5.8,
        hinge_position_m=0.09375,
        tip_segment_length_m=0.03125,
        theta_min_deg=-45.0,
    )


def test_theta_min_maps_to_folded_display_angle() -> None:
    progress = deployment_progress_from_theta(-45.0, theta_min_deg=-45.0)
    assert progress == pytest.approx(0.0)
    assert display_hinge_angle_from_progress(progress) == pytest.approx(
        CONCEPT_FOLDED_DISPLAY_ANGLE_DEG
    )


def test_theta_max_maps_to_open_display_angle() -> None:
    progress = deployment_progress_from_theta(0.0, theta_min_deg=-45.0)
    assert progress == pytest.approx(1.0)
    assert display_hinge_angle_from_progress(progress) == pytest.approx(
        CONCEPT_OPEN_DISPLAY_ANGLE_DEG
    )


def test_out_of_range_theta_is_clamped() -> None:
    low = deployment_progress_from_theta(-90.0, theta_min_deg=-45.0)
    high = deployment_progress_from_theta(10.0, theta_min_deg=-45.0)
    assert low == pytest.approx(0.0)
    assert high == pytest.approx(1.0)


def test_frame_folded_reference_is_progress_zero() -> None:
    frame = frame_folded_reference()
    assert frame.deployment_progress_01 == pytest.approx(0.0)
    assert frame.display_hinge_angle_deg == pytest.approx(180.0)
    assert frame.time_s == pytest.approx(0.0)


def test_frame_at_progress_sets_pseudo_time() -> None:
    state = _rt75_state(theta_deg=-10.0)
    frame = frame_at_progress(state, 0.5)
    assert frame.deployment_progress_01 == pytest.approx(0.5)
    assert frame.time_s == pytest.approx(0.5 * DEPLOYMENT_SEQUENCE_DURATION_S)


def test_folded_tip_before_hinge_open_tip_beyond() -> None:
    folded = frame_folded_reference()
    open_frame = frame_from_state(_rt75_state(theta_deg=0.0))
    folded_x, _ = display_tip_point(folded)
    open_x, _ = display_tip_point(open_frame)
    assert folded_x < folded.hinge_position_m
    assert open_x == pytest.approx(0.125)


def test_draw_deployment_sequence_writes_png(tmp_path: Path) -> None:
    state = _rt75_state(theta_deg=-5.0)
    output = tmp_path / "concept_deployment_sequence.png"
    draw_deployment_sequence(state, output_path=output)
    assert output.is_file()
    assert output.stat().st_size > 0


def test_export_deployment_frames_writes_manifest(tmp_path: Path) -> None:
    state = _rt75_state(theta_deg=-5.0)
    manifest = export_deployment_frames(state, tmp_path, progress_values=[0.0, 1.0])
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["frame_count"] == 2
    assert payload["frames"][0]["deployment_progress_01"] == pytest.approx(0.0)
    assert payload["frames"][-1]["deployment_progress_01"] == pytest.approx(1.0)
    assert (manifest.parent / "frame_0000.png").is_file()
    assert (manifest.parent / "frame_0001.png").is_file()
