"""Physics-debug figures for prescribed-RPM foldable simulations."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .physics_state import PhysicsState


def plot_physics_debug_figures(
    states: Sequence[PhysicsState],
    output_dir: str | Path,
    *,
    prefix: str = "physics",
) -> list[Path]:
    """Write five physics-debug PNG figures."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not states:
        return []

    times = [s.time_s for s in states]
    written: list[Path] = []

    # 1. theta / theta_dot / theta_ddot vs time
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 8.0), sharex=True)
    axes[0].plot(times, [s.theta_deg for s in states], "k-", lw=1.0)
    axes[0].set_ylabel("theta (deg)")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(times, [s.theta_dot_deg_s for s in states], "k-", lw=1.0)
    axes[1].set_ylabel("theta_dot (deg/s)")
    axes[1].grid(True, alpha=0.3)
    axes[2].plot(times, [s.theta_ddot_deg_s2 for s in states], "k-", lw=1.0)
    axes[2].set_ylabel("theta_ddot (deg/s²)")
    axes[2].set_xlabel("Time (s)")
    axes[2].grid(True, alpha=0.3)
    fig.suptitle("Hinge kinematics")
    fig.tight_layout()
    p1 = out / f"{prefix}_hinge_kinematics.png"
    fig.savefig(p1, dpi=120, facecolor="white")
    plt.close(fig)
    written.append(p1)

    # 2. Moment components vs time
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    for label, key in [
        ("M_cent", "M_centrifugal_nm"),
        ("M_aero", "M_aero_nm"),
        ("M_stiff", "M_stiffness_nm"),
        ("M_damp", "M_damping_nm"),
        ("M_fric", "M_friction_nm"),
        ("M_stop", "M_stop_nm"),
        ("M_net", "M_net_nm"),
    ]:
        ax.plot(times, [getattr(s, key) for s in states], lw=1.0, label=label)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Moment (N·m)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_title("Hinge moment components")
    fig.tight_layout()
    p2 = out / f"{prefix}_moments.png"
    fig.savefig(p2, dpi=120, facecolor="white")
    plt.close(fig)
    written.append(p2)

    # 3. thrust_root / thrust_tip / thrust_total vs time
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.plot(times, [s.thrust_root_n for s in states], label="root", lw=1.0)
    ax.plot(times, [s.thrust_tip_n for s in states], label="tip", lw=1.0)
    ax.plot(times, [s.thrust_total_n for s in states], label="total", lw=1.2, color="k")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Thrust (N)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_title("Split thrust")
    fig.tight_layout()
    p3 = out / f"{prefix}_thrust_split.png"
    fig.savefig(p3, dpi=120, facecolor="white")
    plt.close(fig)
    written.append(p3)

    # 4. geometric vs aerodynamic D_eff vs time
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.plot(
        times,
        [s.geometric_effective_diameter_m for s in states],
        label="D_geo",
        lw=1.0,
    )
    ax.plot(
        times,
        [s.aerodynamic_effective_diameter_m for s in states],
        label="D_aero",
        lw=1.0,
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Diameter (m)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_title("Geometric vs aerodynamic effective diameter")
    fig.tight_layout()
    p4 = out / f"{prefix}_diameter_geo_aero.png"
    fig.savefig(p4, dpi=120, facecolor="white")
    plt.close(fig)
    written.append(p4)

    # 5. Phase portrait theta vs theta_dot
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    ax.plot(
        [s.theta_deg for s in states],
        [s.theta_dot_deg_s for s in states],
        "k-",
        lw=1.0,
    )
    ax.set_xlabel("theta (deg)")
    ax.set_ylabel("theta_dot (deg/s)")
    ax.grid(True, alpha=0.3)
    ax.set_title("Phase portrait: theta vs theta_dot")
    fig.tight_layout()
    p5 = out / f"{prefix}_phase_portrait.png"
    fig.savefig(p5, dpi=120, facecolor="white")
    plt.close(fig)
    written.append(p5)

    return written
