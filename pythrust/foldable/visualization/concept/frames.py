"""Frame export for future concept deployment animation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ..state import PropellerVisualState
from .deployment_mapping import frame_at_progress
from .schematic import draw_state_on_axis
from .style import DEFAULT_DEPLOYMENT_PROGRESS_STEPS


def export_deployment_frames(
    state: PropellerVisualState,
    output_dir: str | Path,
    *,
    progress_values: Sequence[float] = DEFAULT_DEPLOYMENT_PROGRESS_STEPS,
    sequence_name: str = "deployment",
) -> Path:
    """Export per-frame PNGs and manifest.json for animation pipelines."""
    base_dir = Path(output_dir) / state.variant_id / sequence_name
    base_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: List[dict[str, float | int | str]] = []
    written_paths: List[Path] = []

    for index, progress in enumerate(progress_values):
        frame = frame_at_progress(state, progress)
        frame_path = base_dir / f"frame_{index:04d}.png"

        fig, axis = plt.subplots(figsize=(4.5, 4.0))
        draw_state_on_axis(axis, frame, title=f"t={frame.time_s:.2f}s")
        fig.savefig(frame_path, dpi=150, facecolor="white")
        plt.close(fig)

        written_paths.append(frame_path)
        manifest_entries.append(
            {
                "frame_index": index,
                "filename": frame_path.name,
                "time_s": frame.time_s if frame.time_s is not None else 0.0,
                "deployment_progress_01": frame.deployment_progress_01,
                "display_hinge_angle_deg": frame.display_hinge_angle_deg,
                "theta_deg_model": frame.theta_deg,
                "throttle": frame.throttle,
                "rpm": frame.rpm,
                "hinge_state": frame.hinge_state,
            }
        )

    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "variant_id": state.variant_id,
                "sequence_name": sequence_name,
                "frame_count": len(manifest_entries),
                "frames": manifest_entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path
