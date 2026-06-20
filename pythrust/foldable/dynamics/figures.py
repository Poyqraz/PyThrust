"""Summary time-history plots for dynamic spin-up."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .calibration import SpinUpCheckpointSummary, TUBITAK_PRETEST_RPM
from .state import DynamicState
from .throttle import ThrottleProfileName


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
    lines = [f"TÜBİTAK @ {checkpoint.checkpoint_rpm:.0f} rpm"]
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


def _annotate_checkpoint(
    axes,
    checkpoint: SpinUpCheckpointSummary,
    *,
    checkpoint_rpm: float = TUBITAK_PRETEST_RPM,
) -> None:
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

    annotation = _format_checkpoint_annotation(checkpoint)
    rpm_axis.annotate(
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


def plot_spinup_summary(
    states: Sequence[DynamicState],
    output_path: str | Path,
    *,
    variant_label: str,
    throttle_profile: ThrottleProfileName = "step",
    ramp_time_s: float | None = None,
    checkpoint: SpinUpCheckpointSummary | None = None,
) -> Path:
    """Write 4-panel figure: RPM, theta, thrust, D_eff vs time."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    times = [row.time_s for row in states]
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.4))

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

    if checkpoint is not None:
        _annotate_checkpoint(axes, checkpoint)

    profile_line = _profile_caption(throttle_profile, ramp_time_s)
    fig.suptitle(f"Dynamic spin-up — {variant_label}", fontsize=12, y=0.98)
    caption = f"{profile_line}\n{_model_notes_line()}"
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
