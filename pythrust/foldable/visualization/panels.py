"""Multi-panel foldable propeller schematic composers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ..variants import DEFAULT_ROOT_TIP_RATIOS, variant_id_from_ratios
from .geometry_2d import plot_limits
from .schematic import MODEL_NOTE_LINES, draw_state_on_axis
from .state import PropellerVisualState

DEFAULT_THROTTLE_SWEEP_VALUES: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _states_for_variant(
    states: Sequence[PropellerVisualState],
    variant_id: str,
) -> List[PropellerVisualState]:
    return [state for state in states if state.variant_id == variant_id]


def _shared_limits(states: Sequence[PropellerVisualState]) -> tuple[float, float, float, float]:
    limits = [plot_limits(state) for state in states]
    xmin = min(item[0] for item in limits)
    xmax = max(item[1] for item in limits)
    ymin = min(item[2] for item in limits)
    ymax = max(item[3] for item in limits)
    return (xmin, xmax, ymin, ymax)


def draw_throttle_sweep_panel(
    variant_id: str,
    states: Sequence[PropellerVisualState],
    *,
    throttles: Sequence[float] = DEFAULT_THROTTLE_SWEEP_VALUES,
    output_path: str | Path,
) -> Path:
    """Side-by-side throttle states for one variant (2x3 grid)."""
    variant_states = _states_for_variant(states, variant_id)
    by_throttle: Dict[float, PropellerVisualState] = {
        round(state.throttle, 4): state for state in variant_states
    }
    selected = [by_throttle[round(value, 4)] for value in throttles if round(value, 4) in by_throttle]
    if not selected:
        raise ValueError(f"No throttle states found for variant {variant_id}")

    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    xmin, xmax, ymin, ymax = _shared_limits(selected)

    for axis, state in zip(axes.flatten(), selected):
        draw_state_on_axis(
            axis,
            state,
            title=f"thr={state.throttle:.1f}",
            show_annotations=False,
        )
        axis.set_xlim(xmin, xmax)
        axis.set_ylim(ymin, ymax)

    for axis in axes.flatten()[len(selected) :]:
        axis.axis("off")

    fig.suptitle(f"Throttle sweep — {variant_id}", fontsize=11)
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
    fig.subplots_adjust(bottom=0.06, top=0.92)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def draw_variant_compare_panel(
    throttle: float,
    states: Sequence[PropellerVisualState],
    *,
    ratios: Sequence[tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
    output_path: str | Path,
) -> Path:
    """Compare default root/tip variants at a fixed throttle (1x5 grid)."""
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

    fig, axes = plt.subplots(1, len(selected), figsize=(3.2 * len(selected), 4.2))
    if len(selected) == 1:
        axes = [axes]

    xmin, xmax, ymin, ymax = _shared_limits(selected)
    for axis, state in zip(axes, selected):
        label = f"RT{state.root_ratio}_{state.tip_ratio}"
        draw_state_on_axis(
            axis,
            state,
            title=label,
            show_annotations=False,
        )
        axis.set_xlim(xmin, xmax)
        axis.set_ylim(ymin, ymax)
        axis.text(
            0.02,
            0.98,
            (
                f"θ={state.theta_deg:.1f}°\n"
                f"D_eff={state.effective_diameter_m:.3f} m\n"
                f"{state.hinge_state}"
            ),
            transform=axis.transAxes,
            fontsize=7,
            va="top",
            ha="left",
            family="monospace",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
        )

    fig.suptitle(f"Variant comparison @ throttle={throttle:.1f}", fontsize=11)
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
    fig.subplots_adjust(bottom=0.08, top=0.88)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path
