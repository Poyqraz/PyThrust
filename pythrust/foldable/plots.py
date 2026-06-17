"""Katlanabilir pervane rapor grafikleri (matplotlib)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .decision import read_design_variant_summary_csv


def read_sweep_csv_for_plots(path: str | Path) -> List[Dict[str, Any]]:
    """Sweep CSV dosyasını grafik için gerekli alanlarla oku."""
    sweep_path = Path(path)
    with sweep_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {sweep_path}")
        return [
            {
                "variant_id": row["variant_id"],
                "throttle": float(row["throttle"]),
                "theta_deg": float(row["theta_deg"]),
                "effective_diameter_m": float(row["effective_diameter_m"]),
                "foldable_thrust_n": float(row["foldable_thrust_n"]),
                "thrust_difference_percent": float(row["thrust_difference_percent"]),
            }
            for row in reader
        ]

FOLDABLE_REPORT_FIGURE_NAMES: tuple[str, ...] = (
    "theta_deg_vs_throttle_by_variant.png",
    "effective_diameter_m_vs_throttle_by_variant.png",
    "foldable_thrust_n_vs_throttle_by_variant.png",
    "thrust_difference_percent_vs_throttle_by_variant.png",
    "flight_startup_scores_by_variant.png",
)

SWEEP_THROTTLE_PLOTS: tuple[tuple[str, str, str], ...] = (
    ("theta_deg", "theta_deg_vs_throttle_by_variant.png", "Hinge angle vs throttle"),
    (
        "effective_diameter_m",
        "effective_diameter_m_vs_throttle_by_variant.png",
        "Effective diameter vs throttle",
    ),
    (
        "foldable_thrust_n",
        "foldable_thrust_n_vs_throttle_by_variant.png",
        "Foldable thrust vs throttle",
    ),
    (
        "thrust_difference_percent",
        "thrust_difference_percent_vs_throttle_by_variant.png",
        "Thrust difference vs throttle",
    ),
)

DECISION_SCORE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("startup_thrust_score", "Startup"),
    ("deployment_score", "Deployment"),
    ("flight_performance_score", "Flight"),
    ("takeoff_transition_score", "Takeoff"),
)


def _group_sweep_by_variant(
    sweep_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in sweep_rows:
        variant_id = str(row["variant_id"])
        grouped.setdefault(variant_id, []).append(dict(row))
    for variant_id in grouped:
        grouped[variant_id].sort(key=lambda item: float(item["throttle"]))
    return grouped


def _variant_label(variant_id: str) -> str:
    prefix = "TIP_HINGED_250_RT"
    if variant_id.startswith(prefix):
        return variant_id[len(prefix) :]
    return variant_id


def read_design_variant_decision_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Karar matrisi CSV dosyasını oku."""
    decision_path = Path(path)
    with decision_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {decision_path}")
        return [dict(row) for row in reader]


def plot_sweep_metric_vs_throttle(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    y_column: str,
    title: str,
    output_path: str | Path,
    ylabel: str | None = None,
) -> Path:
    """Sweep verisinden varyant başına throttle grafiği üret."""
    grouped = _group_sweep_by_variant(sweep_rows)
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axis = plt.subplots(figsize=(8, 5))
    for variant_id in sorted(grouped):
        rows = grouped[variant_id]
        throttles = [float(row["throttle"]) for row in rows]
        values = [float(row[y_column]) for row in rows]
        axis.plot(throttles, values, marker="o", label=_variant_label(variant_id))

    axis.set_xlabel("Throttle")
    axis.set_ylabel(ylabel or y_column)
    axis.set_title(title)
    axis.grid(True, linestyle="--", alpha=0.4)
    axis.legend(title="Variant", fontsize=8)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def plot_decision_scores_by_variant(
    decision_rows: Sequence[Mapping[str, Any]],
    *,
    output_path: str | Path,
) -> Path:
    """Karar skorlarını varyant başına gruplu çubuk grafik olarak çiz."""
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    variant_ids = [str(row["variant_id"]) for row in decision_rows]
    labels = [_variant_label(variant_id) for variant_id in variant_ids]
    score_count = len(DECISION_SCORE_COLUMNS)
    bar_width = 0.18
    x_positions = list(range(len(labels)))

    fig, axis = plt.subplots(figsize=(10, 5))
    for index, (column, legend_label) in enumerate(DECISION_SCORE_COLUMNS):
        offsets = [x + (index - (score_count - 1) / 2) * bar_width for x in x_positions]
        values = [float(row[column]) for row in decision_rows]
        axis.bar(offsets, values, width=bar_width, label=legend_label)

    axis.set_xticks(x_positions)
    axis.set_xticklabels(labels)
    axis.set_xlabel("Variant")
    axis.set_ylabel("Normalized score")
    axis.set_ylim(0.0, 1.05)
    axis.set_title("Flight-startup decision scores by variant")
    axis.grid(True, axis="y", linestyle="--", alpha=0.4)
    axis.legend()
    fig.tight_layout()
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def generate_sweep_figures(
    sweep_csv_path: str | Path,
    figures_dir: str | Path,
) -> List[Path]:
    """Sweep CSV'den throttle tabanlı grafikleri üret."""
    sweep_rows = read_sweep_csv_for_plots(sweep_csv_path)
    output_dir = Path(figures_dir)
    written: List[Path] = []
    for y_column, filename, title in SWEEP_THROTTLE_PLOTS:
        written.append(
            plot_sweep_metric_vs_throttle(
                sweep_rows,
                y_column=y_column,
                title=title,
                output_path=output_dir / filename,
            )
        )
    return written


def generate_decision_figure(
    decision_csv_path: str | Path,
    figures_dir: str | Path,
) -> Path:
    """Karar matrisi skor grafiğini üret."""
    decision_rows = read_design_variant_decision_csv(decision_csv_path)
    return plot_decision_scores_by_variant(
        decision_rows,
        output_path=Path(figures_dir) / FOLDABLE_REPORT_FIGURE_NAMES[4],
    )


def generate_foldable_report_figures(
    *,
    sweep_csv_path: str | Path,
    summary_csv_path: str | Path,
    decision_csv_path: str | Path,
    figures_dir: str | Path,
) -> List[Path]:
    """Tüm foldable rapor grafiklerini üret."""
    del summary_csv_path  # reserved for future summary overlays
    output_dir = Path(figures_dir)
    written = generate_sweep_figures(sweep_csv_path, output_dir)
    written.append(generate_decision_figure(decision_csv_path, output_dir))
    return written
