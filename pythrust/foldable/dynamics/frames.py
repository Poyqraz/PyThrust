"""Rotating concept-style frame export for dynamic spin-up animation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Circle, Polygon

from ..models import FoldablePropellerConfig
from ..visualization.concept.deployment_geometry import (
    hinge_marker,
    main_blade_polygon,
    motor_attachment,
    secondary_blade_polygon,
)
from ..visualization.concept.style import (
    BG_WHITE,
    EDGE_BLACK,
    FACE_BLACK,
    FIGURE_DPI,
    STATE_FIGSIZE,
)
from .dynamics_frame import concept_frame_from_dynamic, rotor_azimuth_rad
from .state import DynamicState

Point = Tuple[float, float]
PolygonPoints = List[Point]
CircleSpec = Tuple[float, float, float]

DEFAULT_FRAME_COUNT = 30
FRAME_FILENAME_WIDTH = 3


def spinup_frames_dir(output_dir: Path, variant_label: str) -> Path:
    """``outputs/foldable/dynamics/frames/<variant_label>/``."""
    return output_dir / "frames" / variant_label


def _frame_filename(index: int) -> str:
    return f"frame_{index:0{FRAME_FILENAME_WIDTH}d}.png"


def _rotate_point(point: Point, angle_rad: float) -> Point:
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    x, y = point
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)


def _rotate_polygon(polygon: PolygonPoints, angle_rad: float) -> PolygonPoints:
    return [_rotate_point(point, angle_rad) for point in polygon]


def _rotate_circle(circle: CircleSpec, angle_rad: float) -> CircleSpec:
    x, y, radius = circle
    rx, ry = _rotate_point((x, y), angle_rad)
    return (rx, ry, radius)


def _plot_limits(
    main_poly: PolygonPoints,
    secondary_poly: PolygonPoints,
    outer: CircleSpec,
) -> tuple[float, float, float, float]:
    xs = [point[0] for point in main_poly + secondary_poly]
    ys = [point[1] for point in main_poly + secondary_poly]
    span = outer[2]
    xmin = min(min(xs), -span)
    xmax = max(max(xs), span)
    ymin = min(min(ys), -span)
    ymax = max(max(ys), span)
    pad = span * 0.15
    return xmin - pad, xmax + pad, ymin - pad, ymax + pad


def draw_rotated_dynamic_state(
    axis: Axes,
    config: FoldablePropellerConfig,
    dynamic: DynamicState,
    *,
    title: str | None = None,
) -> None:
    """Draw concept blades rotated by ``psi(t)``; motor hub stays fixed."""
    frame = concept_frame_from_dynamic(config, dynamic)
    psi_rad = rotor_azimuth_rad(dynamic)

    main_poly = _rotate_polygon(main_blade_polygon(frame), psi_rad)
    secondary_poly = _rotate_polygon(secondary_blade_polygon(frame), psi_rad)
    outer, inner = motor_attachment(frame)
    hinge = _rotate_circle(hinge_marker(frame), psi_rad)

    axis.add_patch(
        Polygon(
            main_poly,
            closed=True,
            facecolor=FACE_BLACK,
            edgecolor=EDGE_BLACK,
            linewidth=0.8,
            zorder=2,
        )
    )
    axis.add_patch(
        Polygon(
            secondary_poly,
            closed=True,
            facecolor=FACE_BLACK,
            edgecolor=EDGE_BLACK,
            linewidth=0.8,
            zorder=3,
        )
    )
    axis.add_patch(
        Circle(
            (outer[0], outer[1]),
            outer[2],
            facecolor=FACE_BLACK,
            edgecolor=EDGE_BLACK,
            linewidth=0.8,
            zorder=4,
        )
    )
    axis.add_patch(
        Circle(
            (inner[0], inner[1]),
            inner[2],
            facecolor=BG_WHITE,
            edgecolor=EDGE_BLACK,
            linewidth=0.8,
            zorder=5,
        )
    )
    axis.add_patch(
        Circle(
            (hinge[0], hinge[1]),
            hinge[2],
            facecolor=BG_WHITE,
            edgecolor=EDGE_BLACK,
            linewidth=1.0,
            zorder=6,
        )
    )

    xmin, xmax, ymin, ymax = _plot_limits(main_poly, secondary_poly, outer)
    axis.set_xlim(xmin, xmax)
    axis.set_ylim(ymin, ymax)
    axis.set_aspect("equal", adjustable="box")
    axis.set_facecolor(BG_WHITE)
    axis.axis("off")
    if title:
        axis.set_title(title, fontsize=9, pad=6)


def _sample_states(
    states: Sequence[DynamicState],
    frame_count: int,
) -> list[DynamicState]:
    if not states:
        return []
    if len(states) <= frame_count:
        return list(states)
    last_index = len(states) - 1
    indices = [round(i * last_index / (frame_count - 1)) for i in range(frame_count)]
    return [states[index] for index in indices]


def export_spinup_frames(
    states: Sequence[DynamicState],
    config: FoldablePropellerConfig,
    output_dir: Path,
    *,
    variant_label: str,
    frame_count: int = DEFAULT_FRAME_COUNT,
) -> list[Path]:
    """Export sampled PNG frames with rotor azimuth rotation."""
    frames_dir = spinup_frames_dir(output_dir, variant_label)
    frames_dir.mkdir(parents=True, exist_ok=True)

    sampled = _sample_states(states, frame_count)
    written: list[Path] = []
    manifest_rows: list[dict[str, float | int | str]] = []

    for index, dynamic in enumerate(sampled):
        fig, axis = plt.subplots(figsize=STATE_FIGSIZE)
        title = f"t={dynamic.time_s:.2f} s  rpm={dynamic.rpm:.0f}"
        draw_rotated_dynamic_state(axis, config, dynamic, title=title)
        path = frames_dir / _frame_filename(index)
        fig.savefig(path, dpi=FIGURE_DPI, facecolor=BG_WHITE, bbox_inches="tight")
        plt.close(fig)
        written.append(path)
        manifest_rows.append(
            {
                "frame_index": index,
                "filename": path.name,
                "time_s": dynamic.time_s,
                "rpm": dynamic.rpm,
                "theta_deg": dynamic.theta_deg,
                "rotor_azimuth_deg": dynamic.rotor_azimuth_deg,
                "effective_diameter_m": dynamic.effective_diameter_m,
                "hinge_state": dynamic.hinge_state,
            }
        )

    manifest = {
        "variant_label": variant_label,
        "frame_count": len(written),
        "dynamic_rotation": True,
        "frames": manifest_rows,
    }
    (frames_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return written


def iter_evenly_spaced_states(
    states: Sequence[DynamicState],
    frame_count: int,
) -> Iterable[DynamicState]:
    """Yield evenly spaced states for tests."""
    return iter(_sample_states(states, frame_count))
