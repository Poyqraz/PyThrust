"""Pure 2D geometry for concept/report blade schematics."""

from __future__ import annotations

import math
from typing import List, Tuple

from ..state import PropellerVisualState
from .deployment_frame import ConceptDeploymentFrame
from .deployment_mapping import frame_folded_reference, frame_from_state
from .style import (
    BLADE_WIDTH_FRACTION,
    HINGE_MARKER_RADIUS_FRACTION,
    MOTOR_INNER_RADIUS_FRACTION,
    MOTOR_OUTER_RADIUS_FRACTION,
)

Point = Tuple[float, float]
Polygon = List[Point]
Circle = Tuple[float, float, float]


def blade_width_m(frame: ConceptDeploymentFrame) -> float:
    return frame.diameter_open_m * BLADE_WIDTH_FRACTION


def _segment_polygon(start: Point, end: Point, half_width: float) -> Polygon:
    """Axis-aligned or angled blade strip as a 4-vertex polygon."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return [start, start, start, start]
    nx = -dy / length * half_width
    ny = dx / length * half_width
    return [
        (start[0] + nx, start[1] + ny),
        (end[0] + nx, end[1] + ny),
        (end[0] - nx, end[1] - ny),
        (start[0] - nx, start[1] - ny),
    ]


def hinge_point(frame: ConceptDeploymentFrame) -> Point:
    return (frame.hinge_position_m, 0.0)


def display_tip_point(frame: ConceptDeploymentFrame) -> Point:
    """Secondary blade tip from visualization-only display_hinge_angle_deg."""
    phi_rad = math.radians(frame.display_hinge_angle_deg)
    hinge_x = frame.hinge_position_m
    length = frame.tip_segment_length_m
    tip_x = hinge_x + length * math.cos(phi_rad)
    tip_y = length * math.sin(phi_rad)
    return (tip_x, tip_y)


def main_blade_polygon(frame: ConceptDeploymentFrame) -> Polygon:
    """Hub to hinge — Ana Kanat / Main blade."""
    half_width = blade_width_m(frame) / 2.0
    return _segment_polygon((0.0, 0.0), hinge_point(frame), half_width)


def secondary_blade_polygon(frame: ConceptDeploymentFrame) -> Polygon:
    """Hinge to tip — İkincil Kanat / Secondary blade (concept deployment angle)."""
    half_width = blade_width_m(frame) / 2.0
    return _segment_polygon(hinge_point(frame), display_tip_point(frame), half_width)


def hinge_marker(frame: ConceptDeploymentFrame) -> Circle:
    """Visible hinge joint at (cx, cy, radius_m)."""
    hinge_x, hinge_y = hinge_point(frame)
    radius = frame.diameter_open_m * HINGE_MARKER_RADIUS_FRACTION
    return (hinge_x, hinge_y, radius)


def motor_attachment(frame: ConceptDeploymentFrame) -> tuple[Circle, Circle]:
    """Stylized motor hub (outer disk, inner hole) centered at hub."""
    outer_r = frame.diameter_open_m * MOTOR_OUTER_RADIUS_FRACTION
    inner_r = frame.diameter_open_m * MOTOR_INNER_RADIUS_FRACTION
    return ((0.0, 0.0, outer_r), (0.0, 0.0, inner_r))


def plot_limits(frame: ConceptDeploymentFrame, *, label_margin: bool = False) -> tuple[float, float, float, float]:
    """Symmetric axis limits for concept schematics."""
    tip_x, tip_y = display_tip_point(frame)
    span = max(
        frame.diameter_open_m / 2.0,
        abs(tip_x),
        abs(tip_y),
        frame.hinge_position_m + frame.tip_segment_length_m,
        frame.hinge_position_m,
    )
    margin_fraction = 0.35 if label_margin else 0.15
    margin = span * margin_fraction
    limit = span + margin
    return (-limit * 0.15, limit, -limit, limit * 0.85)


def concept_info_lines(frame: ConceptDeploymentFrame) -> List[str]:
    """Compact info box lines for single-state concept schematic."""
    return [
        f"{frame.variant_id}",
        f"thr={frame.throttle:.2f}  rpm={frame.rpm:.0f}",
        f"hinge: {frame.hinge_state}",
        f"θ_model={frame.theta_deg:.1f}°  φ_display={frame.display_hinge_angle_deg:.1f}°",
        f"D_eff={frame.effective_diameter_m:.3f} m",
        f"M_open={frame.opening_moment_nm:.3f} Nm",
        f"M_resist={frame.resisting_moment_nm:.3f} Nm",
        f"T_fold={frame.foldable_thrust_n:.2f} N",
    ]


def static_folded_frame() -> ConceptDeploymentFrame:
    """Folded-start reference for static concept overview."""
    return frame_folded_reference()


def frame_for_state(state: PropellerVisualState) -> ConceptDeploymentFrame:
    """Map model visual state to concept deployment frame."""
    return frame_from_state(state)
