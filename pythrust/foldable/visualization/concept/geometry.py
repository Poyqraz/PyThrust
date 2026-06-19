"""Facade re-exporting concept deployment geometry helpers."""

from __future__ import annotations

from typing import List

from ..state import PropellerVisualState
from .deployment_frame import ConceptDeploymentFrame
from .deployment_geometry import (
    blade_width_m,
    display_tip_point,
    hinge_marker,
    hinge_point,
    main_blade_polygon,
    motor_attachment,
    plot_limits,
    secondary_blade_polygon,
)
from .deployment_mapping import frame_folded_reference, frame_from_state


def concept_info_lines(frame: ConceptDeploymentFrame) -> List[str]:
    """Compact info box lines for single-state concept schematic."""
    time_note = f"  t={frame.time_s:.2f}s" if frame.time_s is not None else ""
    return [
        f"{frame.variant_id}",
        f"thr={frame.throttle:.2f}  rpm={frame.rpm:.0f}",
        f"hinge: {frame.hinge_state}",
        f"prog={frame.deployment_progress_01:.2f}{time_note}",
        f"θ_model={frame.theta_deg:.1f}°  φ_display={frame.display_hinge_angle_deg:.1f}°",
        f"D_eff={frame.effective_diameter_m:.3f} m",
        f"M_open={frame.opening_moment_nm:.3f} Nm",
        f"M_resist={frame.resisting_moment_nm:.3f} Nm",
        f"T_fold={frame.foldable_thrust_n:.2f} N",
    ]


def static_folded_frame() -> ConceptDeploymentFrame:
    return frame_folded_reference()


def frame_for_state(state: PropellerVisualState) -> ConceptDeploymentFrame:
    return frame_from_state(state)


__all__ = [
    "blade_width_m",
    "concept_info_lines",
    "display_tip_point",
    "frame_for_state",
    "hinge_marker",
    "hinge_point",
    "main_blade_polygon",
    "motor_attachment",
    "plot_limits",
    "secondary_blade_polygon",
    "static_folded_frame",
]
