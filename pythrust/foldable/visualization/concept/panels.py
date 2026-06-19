"""Multi-panel concept/report schematic composers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ...variants import DEFAULT_ROOT_TIP_RATIOS, variant_id_from_ratios
from ..panels import DEFAULT_THROTTLE_SWEEP_VALUES
from ..state import PropellerVisualState
from .deployment_mapping import frame_at_progress, frame_from_state
from .style import DEPLOYMENT_SEQUENCE_DURATION_S
from .geometry import plot_limits
from .schematic import draw_state_on_axis
from .style import (
    BG_WHITE,
    CONCEPT_MODEL_NOTE,
    FIGURE_DPI,
    PANEL_COMPARE_FIGSIZE,
    PANEL_SWEEP_FIGSIZE,
    SUBPLOT_LABEL_FONTSIZE,
)


def _states_for_variant(
    states: Sequence[PropellerVisualState],
    variant_id: str,
) -> List[PropellerVisualState]:
    return [state for state in states if state.variant_id == variant_id]


def _shared_limits(states: Sequence[PropellerVisualState]) -> tuple[float, float, float, float]:
    limits = [plot_limits(frame_from_state(state)) for state in states]
    xmin = min(item[0] for item in limits)
    xmax = max(item[1] for item in limits)
    ymin = min(item[2] for item in limits)
    ymax = max(item[3] for item in limits)
    return (xmin, xmax, ymin, ymax)


def _compact_subplot_label(axis, frame) -> None:
    axis.text(
        0.03,
        0.97,
        (
            f"prog={frame.deployment_progress_01:.2f}\n"
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


def _variant_compare_subplot_label(axis, state: PropellerVisualState) -> None:
    variant_label = f"RT{state.root_ratio}_{state.tip_ratio}"
    axis.text(
        0.03,
        0.97,
        (
            f"{variant_label}\n"
            f"θ={state.theta_deg:.1f}°\n"
            f"{state.hinge_state}\n"
            f"D_eff={state.effective_diameter_m:.3f} m"
        ),
        transform=axis.transAxes,
        fontsize=SUBPLOT_LABEL_FONTSIZE,
        va="top",
        ha="left",
        family="monospace",
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.9, "edgecolor": "0.8"},
        zorder=8,
    )


def draw_throttle_sweep_concept(
    variant_id: str,
    states: Sequence[PropellerVisualState],
    *,
    throttles: Sequence[float] = DEFAULT_THROTTLE_SWEEP_VALUES,
    output_path: str | Path,
) -> Path:
    """Concept pseudo-time deployment sweep for one variant (2x3 grid)."""
    variant_states = _states_for_variant(states, variant_id)
    by_throttle: Dict[float, PropellerVisualState] = {
        round(state.throttle, 4): state for state in variant_states
    }
    selected = [by_throttle[round(value, 4)] for value in throttles if round(value, 4) in by_throttle]
    if not selected:
        raise ValueError(f"No throttle states found for variant {variant_id}")

    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(selected)
    frames = []
    for index, state in enumerate(selected):
        progress = index / (n - 1) if n > 1 else 0.0
        time_s = progress * DEPLOYMENT_SEQUENCE_DURATION_S
        frames.append(frame_at_progress(state, progress, time_s=time_s))

    fig, axes = plt.subplots(2, 3, figsize=PANEL_SWEEP_FIGSIZE)
    limits = [plot_limits(frame) for frame in frames]
    xmin = min(item[0] for item in limits)
    xmax = max(item[1] for item in limits)
    ymin = min(item[2] for item in limits)
    ymax = max(item[3] for item in limits)

    for axis, frame in zip(axes.flatten(), frames):
        time_s = frame.time_s if frame.time_s is not None else 0.0
        draw_state_on_axis(axis, frame, title=f"t={time_s:.1f} s")
        axis.set_xlim(xmin, xmax)
        axis.set_ylim(ymin, ymax)
        _compact_subplot_label(axis, frame)

    for axis in axes.flatten()[len(frames) :]:
        axis.axis("off")

    fig.suptitle(
        f"Concept pseudo-time deployment sweep — {variant_id}",
        fontsize=11,
    )
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
    fig.subplots_adjust(bottom=0.06, top=0.92)
    fig.savefig(figure_path, dpi=FIGURE_DPI, facecolor=BG_WHITE)
    plt.close(fig)
    return figure_path


def draw_variant_compare_concept(
    throttle: float,
    states: Sequence[PropellerVisualState],
    *,
    ratios: Sequence[tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
    output_path: str | Path,
) -> Path:
    """Concept deployment-style variant comparison at fixed throttle (1x5 grid)."""
    selected: List[PropellerVisualState] = []
    for root_ratio, tip_ratio in ratios:
        variant_id = variant_id_from_ratios(root_ratio, tip_ratio)
        matches = [
            state
            for state in states
            if state.variant_id == variant_id and abs(state.throttle - throttle) < 1e-6
        ]
        if matches:
            selected.append(matches[0])

    if not selected:
        raise ValueError(f"No variant states at throttle {throttle}")

    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, len(selected), figsize=PANEL_COMPARE_FIGSIZE)
    if len(selected) == 1:
        axes = [axes]

    frames = [frame_from_state(state) for state in selected]
    limits = [plot_limits(frame) for frame in frames]
    xmin = min(item[0] for item in limits)
    xmax = max(item[1] for item in limits)
    ymin = min(item[2] for item in limits)
    ymax = max(item[3] for item in limits)

    for axis, state, frame in zip(axes, selected, frames, strict=True):
        variant_label = f"RT{state.root_ratio}_{state.tip_ratio}"
        draw_state_on_axis(axis, frame, title=variant_label)
        axis.set_xlim(xmin, xmax)
        axis.set_ylim(ymin, ymax)
        _variant_compare_subplot_label(axis, state)

    ratio_labels = ", ".join(f"RT{r}_{t}" for r, t in ratios)
    fig.suptitle(
        f"Concept variant comparison @ throttle={throttle:.1f} ({ratio_labels})",
        fontsize=11,
    )
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
