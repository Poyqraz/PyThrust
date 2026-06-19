"""Concept/report schematic visualization for foldable propeller (presentation style)."""

from .deployment_frame import ConceptDeploymentFrame
from .deployment_mapping import (
    deployment_progress_from_theta,
    display_hinge_angle_from_progress,
    frame_folded_reference,
    frame_from_state,
)
from .geometry import display_tip_point, frame_for_state, static_folded_frame
from .panels import draw_throttle_sweep_concept, draw_variant_compare_concept
from .schematic import draw_single_state_concept, draw_static_overview, draw_state_on_axis

__all__ = [
    "ConceptDeploymentFrame",
    "deployment_progress_from_theta",
    "display_hinge_angle_from_progress",
    "display_tip_point",
    "draw_single_state_concept",
    "draw_static_overview",
    "draw_state_on_axis",
    "draw_throttle_sweep_concept",
    "draw_variant_compare_concept",
    "frame_folded_reference",
    "frame_for_state",
    "frame_from_state",
    "static_folded_frame",
]
