"""Map model theta_deg to concept deployment display angles (visualization only)."""

from __future__ import annotations

from ..state import PropellerVisualState
from .deployment_frame import ConceptDeploymentFrame
from .style import (
    CONCEPT_FOLDED_DISPLAY_ANGLE_DEG,
    CONCEPT_OPEN_DISPLAY_ANGLE_DEG,
    DEPLOYMENT_SEQUENCE_DURATION_S,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def deployment_progress_from_theta(
    theta_deg: float,
    *,
    theta_min_deg: float,
    theta_max_deg: float = 0.0,
) -> float:
    """Map model hinge angle to normalized deployment progress in [0, 1]."""
    span = theta_max_deg - theta_min_deg
    if abs(span) < 1e-12:
        return 1.0 if theta_deg >= theta_max_deg else 0.0
    return _clamp01((theta_deg - theta_min_deg) / span)


def display_hinge_angle_from_progress(deployment_progress_01: float) -> float:
    """Interpolate concept display angle: folded (180°) → open (0°)."""
    progress = _clamp01(deployment_progress_01)
    return (
        CONCEPT_FOLDED_DISPLAY_ANGLE_DEG
        + progress * (CONCEPT_OPEN_DISPLAY_ANGLE_DEG - CONCEPT_FOLDED_DISPLAY_ANGLE_DEG)
    )


def pseudo_time_from_progress(deployment_progress_01: float) -> float:
    """Map normalized deployment progress to pseudo-time for sequence visuals."""
    return _clamp01(deployment_progress_01) * DEPLOYMENT_SEQUENCE_DURATION_S


def frame_at_progress(
    state: PropellerVisualState,
    deployment_progress_01: float,
    *,
    time_s: float | None = None,
) -> ConceptDeploymentFrame:
    """Build a concept frame at an explicit deployment progress."""
    progress = _clamp01(deployment_progress_01)
    resolved_time = (
        time_s if time_s is not None else pseudo_time_from_progress(progress)
    )
    return ConceptDeploymentFrame(
        source_state=state,
        deployment_progress_01=progress,
        display_hinge_angle_deg=display_hinge_angle_from_progress(progress),
        time_s=resolved_time,
    )


def frame_from_state(state: PropellerVisualState) -> ConceptDeploymentFrame:
    """Build a concept deployment frame from a model visual state."""
    progress = deployment_progress_from_theta(
        state.theta_deg,
        theta_min_deg=state.theta_min_deg,
        theta_max_deg=0.0,
    )
    return frame_at_progress(state, progress)


def frame_folded_reference() -> ConceptDeploymentFrame:
    """Folded-start reference frame for static concept overview."""
    reference_state = PropellerVisualState(
        variant_id="TIP_HINGED_250_RT75_25",
        root_ratio=75,
        tip_ratio=25,
        throttle=0.0,
        rpm=0.0,
        theta_deg=-45.0,
        effective_diameter_m=0.235,
        opening_moment_nm=0.0,
        resisting_moment_nm=0.0,
        moment_margin_nm=0.0,
        hinge_state="folded",
        foldable_thrust_n=0.0,
        hinge_position_m=0.09375,
        tip_segment_length_m=0.03125,
        diameter_open_m=0.25,
        theta_min_deg=-45.0,
    )
    return ConceptDeploymentFrame(
        source_state=reference_state,
        deployment_progress_01=0.0,
        display_hinge_angle_deg=CONCEPT_FOLDED_DISPLAY_ANGLE_DEG,
        time_s=0.0,
    )
