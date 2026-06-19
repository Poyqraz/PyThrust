"""Pure 2D geometry for concept/report blade schematics."""

from __future__ import annotations

import math
from typing import List, Tuple

from ..state import PropellerVisualState
from .style import (
    BLADE_WIDTH_FRACTION,
    HINGE_MARKER_RADIUS_FRACTION,
    MOTOR_INNER_RADIUS_FRACTION,
    MOTOR_OUTER_RADIUS_FRACTION,
)

Point = Tuple[float, float]
Polygon = List[Point]
Circle = Tuple[float, float, float]


def blade_width_m(state: PropellerVisualState) -> float:
    return state.diameter_open_m * BLADE_WIDTH_FRACTION


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


def hinge_point(state: PropellerVisualState) -> Point:
    return _hinge_point(state)


def tip_point(state: PropellerVisualState) -> Point:
    return _tip_point(state)


def _hinge_point(state: PropellerVisualState) -> Point:
    return (state.hinge_position_m, 0.0)


def _tip_point(state: PropellerVisualState) -> Point:
    theta_rad = math.radians(state.theta_deg)
    hinge_x = state.hinge_position_m
    tip_x = hinge_x + state.tip_segment_length_m * math.cos(theta_rad)
    tip_y = state.tip_segment_length_m * math.sin(theta_rad)
    return (tip_x, tip_y)


def main_blade_polygon(state: PropellerVisualState) -> Polygon:
    """Hub to hinge — Ana Kanat / Main blade."""
    half_width = blade_width_m(state) / 2.0
    return _segment_polygon((0.0, 0.0), _hinge_point(state), half_width)


def secondary_blade_polygon(state: PropellerVisualState) -> Polygon:
    """Hinge to tip — İkincil Kanat / Secondary blade (follows theta_deg)."""
    half_width = blade_width_m(state) / 2.0
    return _segment_polygon(_hinge_point(state), _tip_point(state), half_width)


def hinge_marker(state: PropellerVisualState) -> Circle:
    """Visible hinge joint at (cx, cy, radius_m)."""
    hinge_x, hinge_y = _hinge_point(state)
    radius = state.diameter_open_m * HINGE_MARKER_RADIUS_FRACTION
    return (hinge_x, hinge_y, radius)


def motor_attachment(state: PropellerVisualState) -> tuple[Circle, Circle]:
    """Stylized motor hub (outer disk, inner hole) centered at hub."""
    outer_r = state.diameter_open_m * MOTOR_OUTER_RADIUS_FRACTION
    inner_r = state.diameter_open_m * MOTOR_INNER_RADIUS_FRACTION
    return ((0.0, 0.0, outer_r), (0.0, 0.0, inner_r))


def plot_limits(state: PropellerVisualState, *, label_margin: bool = False) -> tuple[float, float, float, float]:
    """Symmetric axis limits for concept schematics."""
    tip_x, tip_y = _tip_point(state)
    span = max(
        state.diameter_open_m / 2.0,
        abs(tip_x),
        abs(tip_y),
        state.hinge_position_m + state.tip_segment_length_m,
    )
    margin_fraction = 0.35 if label_margin else 0.15
    margin = span * margin_fraction
    limit = span + margin
    return (-limit * 0.15, limit, -limit, limit * 0.85)


def static_reference_state() -> PropellerVisualState:
    """Fully open RT75_25 reference geometry for static concept overview."""
    return PropellerVisualState(
        variant_id="TIP_HINGED_250_RT75_25",
        root_ratio=75,
        tip_ratio=25,
        throttle=0.0,
        rpm=0.0,
        theta_deg=0.0,
        effective_diameter_m=0.25,
        opening_moment_nm=0.0,
        resisting_moment_nm=0.0,
        moment_margin_nm=0.0,
        hinge_state="fully_open",
        foldable_thrust_n=0.0,
        hinge_position_m=0.09375,
        tip_segment_length_m=0.03125,
        diameter_open_m=0.25,
    )


def concept_info_lines(state: PropellerVisualState) -> List[str]:
    """Compact info box lines for single-state concept schematic."""
    return [
        f"{state.variant_id}",
        f"thr={state.throttle:.2f}  rpm={state.rpm:.0f}",
        f"θ={state.theta_deg:.1f}°  D_eff={state.effective_diameter_m:.3f} m",
        f"M_open={state.opening_moment_nm:.3f} Nm",
        f"M_resist={state.resisting_moment_nm:.3f} Nm",
        f"margin={state.moment_margin_nm:.3f} Nm",
        f"hinge: {state.hinge_state}",
        f"T_fold={state.foldable_thrust_n:.2f} N",
    ]
