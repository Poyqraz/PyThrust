"""Concept/report schematic visualization for foldable propeller (presentation style)."""

from .deployment_frame import ConceptDeploymentFrame
from .deployment_mapping import (
    deployment_progress_from_theta,
    display_hinge_angle_from_progress,
    frame_at_progress,
    frame_folded_reference,
    frame_from_state,
    pseudo_time_from_progress,
)
from .deployment_geometry import display_tip_point
from .frames import export_concept_frames_from_states, export_deployment_frames
from .geometry import frame_for_state, static_folded_frame
from .panels import draw_throttle_sweep_concept, draw_variant_compare_concept
from .schematic import draw_single_state_concept, draw_static_overview, draw_state_on_axis
from .sequence import draw_deployment_sequence

__all__ = [
    "ConceptDeploymentFrame",
    "deployment_progress_from_theta",
    "display_hinge_angle_from_progress",
    "display_tip_point",
    "draw_deployment_sequence",
    "draw_single_state_concept",
    "draw_static_overview",
    "draw_state_on_axis",
    "draw_throttle_sweep_concept",
    "draw_variant_compare_concept",
    "export_concept_frames_from_states",
    "export_deployment_frames",
    "frame_at_progress",
    "frame_folded_reference",
    "frame_for_state",
    "frame_from_state",
    "pseudo_time_from_progress",
    "static_folded_frame",
]
