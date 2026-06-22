"""Export concept deployment frames for future animation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ..state import PropellerVisualState
from .deployment_mapping import frame_at_progress
from .schematic import draw_state_on_axis
from .style import (
    BG_WHITE,
    DEFAULT_DEPLOYMENT_PROGRESS_STEPS,
    DEPLOYMENT_SEQUENCE_DURATION_S,
    FIGURE_DPI,
    STATE_FIGSIZE,
)

DEFAULT_FRAME_COUNT = 6
FRAME_FILENAME_WIDTH = 3
LEGACY_FRAME_FILENAME_WIDTH = 4


def concept_frames_dir(output_dir: Path, variant_id: str) -> Path:
    """``outputs/foldable/visuals/frames/concept_<variant_id>/``."""
    return output_dir / "frames" / f"concept_{variant_id}"


def _frame_filename(index: int, *, width: int = FRAME_FILENAME_WIDTH) -> str:
    return f"frame_{index:0{width}d}.png"


def _source_state_id(state: PropellerVisualState) -> str:
    return f"{state.variant_id}_thr_{state.throttle:.1f}"


def _write_frame_png(frame, path: Path, *, title: str) -> None:
    fig, axis = plt.subplots(figsize=STATE_FIGSIZE)
    draw_state_on_axis(axis, frame, title=title)
    fig.savefig(path, dpi=FIGURE_DPI, facecolor=BG_WHITE, bbox_inches="tight")
    plt.close(fig)


def _write_frames_metadata_csv(
    rows: list[dict[str, float | int | str]],
    path: Path,
) -> None:
    fieldnames = [
        "frame_index",
        "filename",
        "time_s",
        "deployment_progress_01",
        "display_hinge_angle_deg",
        "source_throttle",
        "source_theta_deg",
        "source_state_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_concept_frames_from_states(
    states: Sequence[PropellerVisualState],
    output_dir: Path,
    *,
    variant_id: str,
    duration_s: float = DEPLOYMENT_SEQUENCE_DURATION_S,
    write_metadata_csv: bool = True,
) -> list[Path]:
    """Export one PNG per state with pseudo-time labels ``t=0.0 s`` … ``t={duration} s``.

    ``states`` should be ordered from folded (low throttle) to open (high throttle).
    Display hinge angle follows panel index progress, not raw model ``theta_deg``.
    """
    if not states:
        return []

    frames_dir = concept_frames_dir(output_dir, variant_id)
    frames_dir.mkdir(parents=True, exist_ok=True)

    n = len(states)
    written: list[Path] = []
    csv_rows: list[dict[str, float | int | str]] = []

    for index, state in enumerate(states):
        progress = index / (n - 1) if n > 1 else 0.0
        time_s = progress * duration_s
        frame = frame_at_progress(state, progress, time_s=time_s)
        path = frames_dir / _frame_filename(index)
        _write_frame_png(frame, path, title=f"t={time_s:.1f} s")
        written.append(path)
        csv_rows.append(
            {
                "frame_index": index,
                "filename": path.name,
                "time_s": round(time_s, 4),
                "deployment_progress_01": round(frame.deployment_progress_01, 6),
                "display_hinge_angle_deg": round(frame.display_hinge_angle_deg, 4),
                "source_throttle": round(state.throttle, 4),
                "source_theta_deg": round(state.theta_deg, 4),
                "source_state_id": _source_state_id(state),
            }
        )

    manifest = {
        "variant_id": variant_id,
        "frame_count": len(written),
        "duration_s": duration_s,
        "pseudo_time": True,
        "frames_dir": str(frames_dir),
        "frames": [
            {
                "index": row["frame_index"],
                "filename": row["filename"],
                "time_s": row["time_s"],
                "deployment_progress_01": row["deployment_progress_01"],
                "display_hinge_angle_deg": row["display_hinge_angle_deg"],
                "source_throttle": row["source_throttle"],
                "source_theta_deg": row["source_theta_deg"],
                "source_state_id": row["source_state_id"],
            }
            for row in csv_rows
        ],
    }
    manifest_path = frames_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if write_metadata_csv:
        _write_frames_metadata_csv(csv_rows, frames_dir / "frames_metadata.csv")

    return written


def export_deployment_frames(
    state: PropellerVisualState,
    output_dir: str | Path,
    *,
    progress_values: Sequence[float] = DEFAULT_DEPLOYMENT_PROGRESS_STEPS,
    sequence_name: str = "deployment",
) -> Path:
    """Legacy uniform-progress export under ``<output_dir>/<variant_id>/<sequence_name>/``."""
    base_dir = Path(output_dir) / state.variant_id / sequence_name
    base_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: List[dict[str, float | int | str]] = []
    written_paths: List[Path] = []

    for index, progress in enumerate(progress_values):
        frame = frame_at_progress(state, progress)
        frame_path = base_dir / _frame_filename(index, width=LEGACY_FRAME_FILENAME_WIDTH)

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
