"""Summary time-history plots for dynamic spin-up."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .state import DynamicState


def plot_spinup_summary(
    states: Sequence[DynamicState],
    output_path: str | Path,
    *,
    variant_label: str,
) -> Path:
    """Write 4-panel figure: RPM, theta, thrust, D_eff vs time."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    times = [row.time_s for row in states]
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.0))

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

    fig.suptitle(f"Dynamic spin-up — {variant_label}", fontsize=12)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=150, facecolor="white")
    plt.close(fig)
    return figure_path
