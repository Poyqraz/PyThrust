"""Time/progress deployment sequence panel for concept visuals."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ..state import PropellerVisualState
from .deployment_mapping import frame_at_progress
from .deployment_geometry import plot_limits
from .schematic import draw_state_on_axis
from .style import (
    BG_WHITE,
    CONCEPT_MODEL_NOTE,
    DEFAULT_DEPLOYMENT_PROGRESS_STEPS,
    FIGURE_DPI,
    SEQUENCE_FIGSIZE,
    SUBPLOT_LABEL_FONTSIZE,
)


def draw_deployment_sequence(
    state: PropellerVisualState,
    *,
    progress_values: Sequence[float] = DEFAULT_DEPLOYMENT_PROGRESS_STEPS,
    output_path: str | Path,
) -> Path:
    """Render deployment progression from folded (t=0) to open."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    frames = [frame_at_progress(state, value) for value in progress_values]
    fig, axes = plt.subplots(1, len(frames), figsize=SEQUENCE_FIGSIZE)
    if len(frames) == 1:
        axes = [axes]

    xmin = min(plot_limits(frame)[0] for frame in frames)
    xmax = max(plot_limits(frame)[1] for frame in frames)
    ymin = min(plot_limits(frame)[2] for frame in frames)
    ymax = max(plot_limits(frame)[3] for frame in frames)

    for axis, frame in zip(axes, frames):
        time_label = f"t={frame.time_s:.1f}s" if frame.time_s is not None else "t=?"
        draw_state_on_axis(axis, frame, title=time_label)
        axis.set_xlim(xmin, xmax)
        axis.set_ylim(ymin, ymax)
        axis.text(
            0.03,
            0.97,
            (
                f"prog={frame.deployment_progress_01:.1f}\n"
                f"φ={frame.display_hinge_angle_deg:.0f}°"
            ),
            transform=axis.transAxes,
            fontsize=SUBPLOT_LABEL_FONTSIZE,
            va="top",
            ha="left",
            family="monospace",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.9, "edgecolor": "0.8"},
            zorder=8,
        )

    fig.suptitle(f"Concept deployment sequence — {state.variant_id}", fontsize=11)
    fig.text(
        0.01,
        0.01,
        CONCEPT_MODEL_NOTE,
        ha="left",
        va="bottom",
        fontsize=6,
        color="0.4",
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.08, top=0.88)
    fig.savefig(figure_path, dpi=FIGURE_DPI, facecolor=BG_WHITE)
    plt.close(fig)
    return figure_path
