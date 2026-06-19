"""Single-state matplotlib schematics for foldable propeller visualization."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Circle

from ..decision import ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE
from ..kinematics import OPENING_MOMENT_V1_MODEL_NOTE
from .geometry_2d import (
    annotation_lines,
    blade_polylines,
    effective_radius_circle,
    hub_radius_m,
    open_radius_circle,
    open_reference_polylines,
    plot_limits,
    stowed_envelope_circle,
)
from .state import PropellerVisualState

MODEL_NOTE_LINES: tuple[str, ...] = (
    "2D radial schematic / effective-diameter visualization",
    OPENING_MOMENT_V1_MODEL_NOTE,
    ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE,
)


def _draw_blade_polylines(
    axis: Axes,
    polylines: Sequence[Sequence[tuple[float, float]]],
    *,
    root_color: str = "0.25",
    tip_color: str = "tab:blue",
    linestyle: str = "-",
    linewidth: float = 1.8,
    alpha: float = 1.0,
) -> None:
    for polyline in polylines:
        xs = [point[0] for point in polyline]
        ys = [point[1] for point in polyline]
        axis.plot(xs[:2], ys[:2], color=root_color, linestyle=linestyle, linewidth=linewidth, alpha=alpha)
        axis.plot(xs[1:], ys[1:], color=tip_color, linestyle=linestyle, linewidth=linewidth, alpha=alpha)


def _draw_state_on_axis(
    axis: Axes,
    state: PropellerVisualState,
    *,
    show_open_reference: bool = True,
    show_annotations: bool = True,
    title: str | None = None,
) -> None:
    xmin, xmax, ymin, ymax = plot_limits(state)
    axis.set_xlim(xmin, xmax)
    axis.set_ylim(ymin, ymax)
    axis.set_aspect("equal", adjustable="box")
    axis.axhline(0.0, color="0.85", linewidth=0.8, zorder=0)
    axis.axvline(0.0, color="0.85", linewidth=0.8, zorder=0)

    hub_r = hub_radius_m(state)
    axis.add_patch(Circle((0.0, 0.0), hub_r, facecolor="0.2", edgecolor="0.1", zorder=3))

    _, _, open_r = open_radius_circle(state)
    axis.add_patch(
        Circle(
            (0.0, 0.0),
            open_r,
            fill=False,
            linestyle=":",
            linewidth=0.9,
            edgecolor="0.55",
            zorder=1,
        )
    )
    axis.text(
        open_r * 0.72,
        open_r * 0.72,
        f"open target = {state.diameter_open_m:.2f} m",
        fontsize=6.5,
        color="0.45",
        ha="left",
        va="bottom",
    )

    stowed_circle = stowed_envelope_circle(state)
    if stowed_circle is not None:
        _, _, stowed_r = stowed_circle
        axis.add_patch(
            Circle(
                (0.0, 0.0),
                stowed_r,
                fill=False,
                linestyle=(0, (2, 2)),
                linewidth=1.0,
                edgecolor="tab:purple",
                zorder=1,
            )
        )
        axis.text(
            -stowed_r * 0.05,
            -stowed_r * 0.92,
            f"stowed envelope target = {state.stowed_envelope_diameter_m:.2f} m",
            fontsize=6.5,
            color="tab:purple",
            ha="center",
            va="top",
        )

    cx, cy, eff_r = effective_radius_circle(state)
    axis.add_patch(
        Circle(
            (cx, cy),
            eff_r,
            fill=False,
            linestyle="--",
            linewidth=1.0,
            edgecolor="tab:orange",
            zorder=1,
        )
    )
    axis.text(
        eff_r * 0.55,
        -eff_r * 0.85,
        f"D_eff = {state.effective_diameter_m:.3f} m",
        fontsize=6.5,
        color="tab:orange",
        ha="left",
        va="top",
    )

    if show_open_reference and abs(state.theta_deg) > 1e-6:
        _draw_blade_polylines(
            axis,
            open_reference_polylines(state),
            linestyle=":",
            linewidth=1.0,
            alpha=0.45,
            tip_color="0.55",
        )

    polylines = blade_polylines(state)
    _draw_blade_polylines(axis, polylines)

    hinge_x = state.hinge_position_m
    axis.plot(hinge_x, 0.0, marker="o", markersize=4, color="tab:red", zorder=4)
    if state.blade_count > 1:
        axis.plot(-hinge_x, 0.0, marker="o", markersize=4, color="tab:red", zorder=4)

    if title:
        axis.set_title(title, fontsize=9)
    axis.set_xlabel("x (m)", fontsize=8)
    axis.set_ylabel("y (m)", fontsize=8)
    axis.tick_params(labelsize=7)
    axis.grid(True, linestyle="--", alpha=0.25)

    if show_annotations:
        note_text = "\n".join(annotation_lines(state))
        axis.text(
            0.02,
            0.02,
            note_text,
            transform=axis.transAxes,
            fontsize=6.5,
            va="bottom",
            ha="left",
            family="monospace",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
        )


def draw_single_state(
    state: PropellerVisualState,
    *,
    output_path: str | Path,
    title: str | None = None,
) -> Path:
    """Render one engineering schematic PNG for a propeller state."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axis = plt.subplots(figsize=(7, 6))
    panel_title = title or f"{state.variant_id} @ throttle={state.throttle:.2f}"
    _draw_state_on_axis(axis, state, title=panel_title)

    fig.text(
        0.01,
        0.01,
        " | ".join(MODEL_NOTE_LINES),
        ha="left",
        va="bottom",
        fontsize=6,
        color="0.35",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.08)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def draw_state_on_axis(
    axis: Axes,
    state: PropellerVisualState,
    *,
    title: str | None = None,
    show_annotations: bool = False,
) -> None:
    """Draw schematic on an existing matplotlib axis (for panels)."""
    _draw_state_on_axis(
        axis,
        state,
        show_annotations=show_annotations,
        title=title,
    )
