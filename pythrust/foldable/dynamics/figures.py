"""Summary time-history plots for dynamic spin-up."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .calibration import SpinUpCheckpointSummary, CHECKPOINT_RPM
from .state import DynamicState
from .throttle import ThrottleProfileName

SPINUP_REPORT_FIGURE_NOTE = (
    "Report figure: ramp profile preferred for startup visualization; step = ideal full "
    "command. ideal_geometry_ratio is not experimental performance. "
    "current_pretest_ratio=0.70 is pretest reference; "
    "project_target_ratio=0.85 is project target. "
    "Frames are single-arm concept frames, not full two-blade rotor CAD."
)


def _profile_caption(profile: ThrottleProfileName, ramp_time_s: float | None) -> str:
    if profile == "linear_ramp":
        ramp = ramp_time_s if ramp_time_s is not None else 0.5
        return f"input profile: linear_ramp (ramp_time_s={ramp:g} s)"
    return "input profile: step (ideal command)"


def _model_notes_line() -> str:
    return (
        "V1 dynamic model | quasi-static hinge | reference-scaled thrust + "
        "aero_effectiveness | no BEM/CFD/experiment yet"
    )


def _format_checkpoint_annotation(checkpoint: SpinUpCheckpointSummary) -> str:
    lines = [f"Checkpoint @ {checkpoint.checkpoint_rpm:.0f} rpm"]
    if checkpoint.time_to_7100_rpm is not None:
        lines.append(f"t={checkpoint.time_to_7100_rpm:.3f} s")
    if checkpoint.theta_at_7100_rpm is not None:
        lines.append(f"θ={checkpoint.theta_at_7100_rpm:.2f}°")
    if checkpoint.D_eff_at_7100_rpm is not None:
        lines.append(f"D_eff={checkpoint.D_eff_at_7100_rpm:.3f} m")
    if checkpoint.ideal_geometry_ratio_at_7100_rpm is not None:
        lines.append(f"ideal ratio={checkpoint.ideal_geometry_ratio_at_7100_rpm:.3f}")
    lines.append(
        f"pretest ref={checkpoint.current_pretest_ratio:.2f}  "
        f"target={checkpoint.project_target_ratio:.2f}"
    )
    return "\n".join(lines)


def _draw_checkpoint_guides(
    axes,
    checkpoint: SpinUpCheckpointSummary,
    *,
    checkpoint_rpm: float = CHECKPOINT_RPM,
) -> None:
    """Horizontal 7100 rpm line on RPM panel; vertical time line on all panels."""
    rpm_axis = axes[0, 0]
    rpm_axis.axhline(
        checkpoint_rpm,
        color="C3",
        linestyle="--",
        linewidth=0.9,
        alpha=0.75,
        label=f"{checkpoint_rpm:.0f} rpm",
    )

    time_hit = checkpoint.time_to_7100_rpm
    if time_hit is None:
        return

    for axis in axes.flat:
        axis.axvline(time_hit, color="C3", linestyle=":", linewidth=0.9, alpha=0.65)


def _annotate_checkpoint_legacy(
    axes,
    checkpoint: SpinUpCheckpointSummary,
    *,
    checkpoint_rpm: float = CHECKPOINT_RPM,
) -> None:
    """Legacy inline annotation near the RPM trace (backward compatible)."""
    _draw_checkpoint_guides(axes, checkpoint, checkpoint_rpm=checkpoint_rpm)

    time_hit = checkpoint.time_to_7100_rpm
    if time_hit is None:
        return

    annotation = _format_checkpoint_annotation(checkpoint)
    axes[0, 0].annotate(
        annotation,
        xy=(time_hit, checkpoint_rpm),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=7,
        va="bottom",
        ha="left",
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "alpha": 0.88,
            "edgecolor": "0.65",
            "linewidth": 0.6,
        },
    )


def _annotate_checkpoint_report_clean(
    fig,
    axes,
    checkpoint: SpinUpCheckpointSummary,
    *,
    checkpoint_rpm: float = CHECKPOINT_RPM,
) -> None:
    """Place checkpoint text in a reserved right margin (no title overlap)."""
    _draw_checkpoint_guides(axes, checkpoint, checkpoint_rpm=checkpoint_rpm)

    annotation = _format_checkpoint_annotation(checkpoint)
    fig.text(
        0.735,
        0.52,
        annotation,
        transform=fig.transFigure,
        ha="left",
        va="center",
        fontsize=7.5,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": "white",
            "alpha": 0.95,
            "edgecolor": "0.55",
            "linewidth": 0.7,
        },
    )
    fig.text(
        0.735,
        0.865,
        "7100 rpm checkpoint",
        transform=fig.transFigure,
        ha="left",
        va="bottom",
        fontsize=8,
        color="0.35",
        fontweight="bold",
    )


def _plot_panels(axes, states: Sequence[DynamicState]) -> None:
    times = [row.time_s for row in states]

    axes[0, 0].plot(times, [row.rpm for row in states], color="0.15", linewidth=1.2)
    axes[0, 0].set_ylabel("RPM")
    axes[0, 0].set_title("Rotor speed")
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(times, [row.theta_deg for row in states], color="0.15", linewidth=1.2)
    axes[0, 1].set_ylabel("θ (deg)")
    axes[0, 1].set_title("Hinge angle")
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(times, [row.thrust_n for row in states], color="0.15", linewidth=1.2)
    axes[1, 0].set_xlabel("Time (s)")
    axes[1, 0].set_ylabel("Thrust (N)")
    axes[1, 0].set_title("Thrust")
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(
        times,
        [row.effective_diameter_m for row in states],
        color="0.15",
        linewidth=1.2,
    )
    axes[1, 1].set_xlabel("Time (s)")
    axes[1, 1].set_ylabel("D_eff (m)")
    axes[1, 1].set_title("Effective diameter")
    axes[1, 1].grid(True, alpha=0.3)


def plot_spinup_summary(
    states: Sequence[DynamicState],
    output_path: str | Path,
    *,
    variant_label: str,
    throttle_profile: ThrottleProfileName = "step",
    ramp_time_s: float | None = None,
    checkpoint: SpinUpCheckpointSummary | None = None,
    report_clean: bool = False,
) -> Path:
    """Write 4-panel figure: RPM, theta, thrust, D_eff vs time."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    figsize = (10.6, 7.6) if report_clean else (10.0, 7.4)
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    _plot_panels(axes, states)

    if checkpoint is not None:
        if report_clean:
            _annotate_checkpoint_report_clean(fig, axes, checkpoint)
        else:
            _annotate_checkpoint_legacy(axes, checkpoint)

    profile_line = _profile_caption(throttle_profile, ramp_time_s)
    fig.suptitle(f"Dynamic spin-up — {variant_label}", fontsize=12, y=0.98)

    caption_lines = [profile_line, _model_notes_line()]
    if report_clean:
        caption_lines.append(SPINUP_REPORT_FIGURE_NOTE)
    caption = "\n".join(caption_lines)

    if report_clean:
        fig.subplots_adjust(left=0.08, right=0.70, top=0.90, bottom=0.16, hspace=0.38, wspace=0.30)
        fig.text(
            0.5,
            0.02,
            caption,
            ha="center",
            va="bottom",
            fontsize=6.8,
            color="0.35",
            wrap=True,
        )
    else:
        fig.text(
            0.5,
            0.015,
            caption,
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="0.35",
            wrap=True,
        )
        fig.subplots_adjust(bottom=0.11, top=0.93)

    fig.savefig(figure_path, dpi=150, facecolor="white")
    plt.close(fig)
    return figure_path
