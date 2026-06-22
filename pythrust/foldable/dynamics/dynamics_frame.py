"""Build concept-style frames from dynamic simulation states."""

from __future__ import annotations

import math
import re

from ..models import FoldablePropellerConfig
from ..visualization.concept.deployment_frame import ConceptDeploymentFrame
from ..visualization.concept.deployment_mapping import (
    deployment_progress_from_theta,
    display_hinge_angle_from_progress,
)
from ..visualization.state import PropellerVisualState
from .state import DynamicState


def parse_root_tip_ratios(variant_id: str) -> tuple[int, int]:
    """Extract root/tip percentages from ``TIP_HINGED_250_RT75_25`` style ids."""
    match = re.search(r"_RT(\d+)_(\d+)$", variant_id)
    if match is None:
        raise ValueError(f"Cannot parse root/tip ratios from variant_id={variant_id!r}")
    return int(match.group(1)), int(match.group(2))


def visual_state_from_dynamic(
    config: FoldablePropellerConfig,
    dynamic: DynamicState,
) -> PropellerVisualState:
    """Map a dynamic history row to a visualization state container."""
    root_ratio, tip_ratio = parse_root_tip_ratios(config.id)
    margin = dynamic.opening_moment_nm - dynamic.resisting_moment_nm
    return PropellerVisualState(
        variant_id=config.id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        throttle=dynamic.throttle,
        rpm=dynamic.rpm,
        theta_deg=dynamic.theta_deg,
        effective_diameter_m=dynamic.effective_diameter_m,
        opening_moment_nm=dynamic.opening_moment_nm,
        resisting_moment_nm=dynamic.resisting_moment_nm,
        moment_margin_nm=margin,
        hinge_state=dynamic.hinge_state,
        foldable_thrust_n=dynamic.thrust_n,
        hinge_position_m=config.geometry.hinge_position_m,
        tip_segment_length_m=config.geometry.tip_segment_length_m,
        diameter_open_m=config.geometry.diameter_open_m,
        stowed_envelope_diameter_m=config.geometry.stowed_envelope_diameter_m,
        blade_count=config.geometry.blade_count,
        theta_min_deg=config.hinge.theta_min_deg,
    )


def concept_frame_from_dynamic(
    config: FoldablePropellerConfig,
    dynamic: DynamicState,
) -> ConceptDeploymentFrame:
    """Build a concept deployment frame using model theta and folded-start mapping."""
    visual = visual_state_from_dynamic(config, dynamic)
    progress = deployment_progress_from_theta(
        visual.theta_deg,
        theta_min_deg=visual.theta_min_deg,
        theta_max_deg=config.hinge.theta_max_deg,
    )
    return ConceptDeploymentFrame(
        source_state=visual,
        deployment_progress_01=progress,
        display_hinge_angle_deg=display_hinge_angle_from_progress(progress),
        time_s=dynamic.time_s,
    )


def rotor_azimuth_rad(dynamic: DynamicState) -> float:
    return math.radians(dynamic.rotor_azimuth_deg)
