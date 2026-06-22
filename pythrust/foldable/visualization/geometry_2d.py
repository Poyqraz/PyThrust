"""Pure 2D geometry helpers for foldable propeller schematics."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .state import PropellerVisualState

Point = Tuple[float, float]
Polyline = List[Point]

HUB_RADIUS_FRACTION = 0.04


def _rotate_180(point: Point) -> Point:
    x_coord, y_coord = point
    return (-x_coord, -y_coord)


def _single_blade_polyline(state: PropellerVisualState) -> Polyline:
    """Hub → hinge → tip in side elevation (+x radial)."""
    hinge_x = state.hinge_position_m
    theta_rad = math.radians(state.theta_deg)
    tip_x = hinge_x + state.tip_segment_length_m * math.cos(theta_rad)
    tip_y = state.tip_segment_length_m * math.sin(theta_rad)
    return [(0.0, 0.0), (hinge_x, 0.0), (tip_x, tip_y)]


def blade_polylines(state: PropellerVisualState) -> List[Polyline]:
    """Root and tip segments for one or two mirrored blades."""
    primary = _single_blade_polyline(state)
    if state.blade_count <= 1:
        return [primary]
    mirrored = [_rotate_180(point) for point in primary]
    return [primary, mirrored]


def open_reference_polylines(state: PropellerVisualState) -> List[Polyline]:
    """Fully open (theta=0) blade outline for reference overlay."""
    open_state = PropellerVisualState(
        variant_id=state.variant_id,
        root_ratio=state.root_ratio,
        tip_ratio=state.tip_ratio,
        throttle=state.throttle,
        rpm=state.rpm,
        theta_deg=0.0,
        effective_diameter_m=state.diameter_open_m,
        opening_moment_nm=state.opening_moment_nm,
        resisting_moment_nm=state.resisting_moment_nm,
        moment_margin_nm=state.moment_margin_nm,
        hinge_state=state.hinge_state,
        foldable_thrust_n=state.foldable_thrust_n,
        hinge_position_m=state.hinge_position_m,
        tip_segment_length_m=state.tip_segment_length_m,
        diameter_open_m=state.diameter_open_m,
        stowed_envelope_diameter_m=state.stowed_envelope_diameter_m,
        blade_count=state.blade_count,
        theta_min_deg=state.theta_min_deg,
    )
    return blade_polylines(open_state)


def effective_radius_circle(state: PropellerVisualState) -> Tuple[float, float, float]:
    """D_eff circle centered at hub: (cx, cy, radius_m)."""
    return (0.0, 0.0, state.effective_diameter_m / 2.0)


def open_radius_circle(state: PropellerVisualState) -> Tuple[float, float, float]:
    """Nominal open diameter circle centered at hub."""
    return (0.0, 0.0, state.diameter_open_m / 2.0)


def stowed_envelope_circle(state: PropellerVisualState) -> Tuple[float, float, float] | None:
    """Proposal stowed storage envelope circle (documentation reference only)."""
    if state.stowed_envelope_diameter_m is None:
        return None
    return (0.0, 0.0, state.stowed_envelope_diameter_m / 2.0)


def hub_radius_m(state: PropellerVisualState) -> float:
    return state.diameter_open_m * HUB_RADIUS_FRACTION


def plot_limits(state: PropellerVisualState) -> Tuple[float, float, float, float]:
    """Symmetric axis limits (xmin, xmax, ymin, ymax) for schematic panels."""
    stowed_radius = (
        state.stowed_envelope_diameter_m / 2.0
        if state.stowed_envelope_diameter_m is not None
        else 0.0
    )
    span = max(
        state.diameter_open_m / 2.0,
        state.effective_diameter_m / 2.0,
        stowed_radius,
        abs(state.tip_segment_length_m),
    )
    margin = span * 0.12
    limit = span + margin
    return (-limit, limit, -limit, limit)


def annotation_lines(state: PropellerVisualState) -> List[str]:
    """Compact engineering labels for schematic annotation box."""
    return [
        f"variant: {state.variant_id}",
        f"root/tip: {state.root_ratio}/{state.tip_ratio}",
        f"throttle: {state.throttle:.2f}",
        f"rpm: {state.rpm:.0f}",
        f"theta: {state.theta_deg:.1f} deg",
        f"D_eff: {state.effective_diameter_m:.4f} m",
        f"M_open: {state.opening_moment_nm:.4f} Nm",
        f"M_resist: {state.resisting_moment_nm:.4f} Nm",
        f"margin: {state.moment_margin_nm:.4f} Nm",
        f"hinge: {state.hinge_state}",
        f"T_fold: {state.foldable_thrust_n:.3f} N",
    ]


def all_polyline_points(polylines: Sequence[Polyline]) -> List[Point]:
    points: List[Point] = []
    for polyline in polylines:
        points.extend(polyline)
    return points
