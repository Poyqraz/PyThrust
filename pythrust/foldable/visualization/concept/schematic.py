"""Matplotlib renderers for concept/report foldable propeller schematics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Circle, Polygon

from ..state import PropellerVisualState
from .deployment_frame import ConceptDeploymentFrame
from .deployment_mapping import frame_from_state
from .geometry import (
    concept_info_lines,
    frame_for_state,
    hinge_marker,
    main_blade_polygon,
    motor_attachment,
    plot_limits,
    secondary_blade_polygon,
    static_folded_frame,
)
from .labels import draw_static_labels
from .style import (
    BG_WHITE,
    CONCEPT_MODEL_NOTE,
    EDGE_BLACK,
    FACE_BLACK,
    FIGURE_DPI,
    INFO_FONTSIZE,
    STATE_FIGSIZE,
    STATIC_FIGSIZE,
)


def _draw_blade_parts(axis: Axes, frame: ConceptDeploymentFrame) -> None:
    main_poly = main_blade_polygon(frame)
    secondary_poly = secondary_blade_polygon(frame)
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

    outer, inner = motor_attachment(frame)
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

    hx, hy, hr = hinge_marker(frame)
    axis.add_patch(
        Circle(
            (hx, hy),
            hr,
            facecolor=BG_WHITE,
            edgecolor=EDGE_BLACK,
            linewidth=1.0,
            zorder=6,
        )
    )


def _prepare_axis(
    axis: Axes,
    frame: ConceptDeploymentFrame,
    *,
    label_margin: bool = False,
    title: str | None = None,
) -> None:
    xmin, xmax, ymin, ymax = plot_limits(frame, label_margin=label_margin)
    axis.set_xlim(xmin, xmax)
    axis.set_ylim(ymin, ymax)
    axis.set_aspect("equal", adjustable="box")
    axis.set_facecolor(BG_WHITE)
    axis.axis("off")
    if title:
        axis.set_title(title, fontsize=10, pad=8)


def draw_state_on_axis(
    axis: Axes,
    frame: ConceptDeploymentFrame,
    *,
    title: str | None = None,
    show_info_box: bool = False,
    show_static_labels: bool = False,
) -> None:
    """Draw concept deployment schematic on an existing matplotlib axis."""
    _prepare_axis(
        axis,
        frame,
        label_margin=show_static_labels,
        title=title,
    )
    _draw_blade_parts(axis, frame)

    if show_static_labels:
        draw_static_labels(axis, frame)

    if show_info_box:
        info_text = "\n".join(concept_info_lines(frame))
        axis.text(
            0.98,
            0.02,
            info_text,
            transform=axis.transAxes,
            fontsize=INFO_FONTSIZE,
            va="bottom",
            ha="right",
            family="monospace",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.92, "edgecolor": "0.75"},
            zorder=7,
        )


def draw_state_on_axis_from_model(
    axis: Axes,
    state: PropellerVisualState,
    *,
    title: str | None = None,
    show_info_box: bool = False,
    show_static_labels: bool = False,
) -> None:
    """Draw concept schematic from a model PropellerVisualState."""
    draw_state_on_axis(
        axis,
        frame_from_state(state),
        title=title,
        show_info_box=show_info_box,
        show_static_labels=show_static_labels,
    )


def draw_static_overview(*, output_path: str | Path) -> Path:
    """Render static concept overview with folded-start configuration."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    frame = static_folded_frame()
    fig, axis = plt.subplots(figsize=STATIC_FIGSIZE)
    draw_state_on_axis(
        axis,
        frame,
        title="Foldable Propeller — Concept Overview (folded start)",
        show_static_labels=True,
    )
    fig.text(
        0.01,
        0.01,
        CONCEPT_MODEL_NOTE,
        ha="left",
        va="bottom",
        fontsize=6.5,
        color="0.4",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.06)
    fig.savefig(figure_path, dpi=FIGURE_DPI, facecolor=BG_WHITE)
    plt.close(fig)
    return figure_path


def draw_single_state_concept(
    state: PropellerVisualState,
    *,
    output_path: str | Path,
    title: str | None = None,
) -> Path:
    """Render single-state concept schematic driven by model outputs."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    frame = frame_for_state(state)
    fig, axis = plt.subplots(figsize=STATE_FIGSIZE)
    panel_title = title or f"{state.variant_id} @ throttle={state.throttle:.2f}"
    draw_state_on_axis(
        axis,
        frame,
        title=panel_title,
        show_info_box=True,
    )
    fig.text(
        0.01,
        0.01,
        CONCEPT_MODEL_NOTE,
        ha="left",
        va="bottom",
        fontsize=6.5,
        color="0.4",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.06)
    fig.savefig(figure_path, dpi=FIGURE_DPI, facecolor=BG_WHITE)
    plt.close(fig)
    return figure_path
