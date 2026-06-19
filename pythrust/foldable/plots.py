"""Katlanabilir pervane rapor grafikleri (matplotlib)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .decision import (
    ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE,
    read_design_variant_summary_csv,
)
from .kinematics import OPENING_MOMENT_V1_MODEL_NOTE

PROJECT_OPEN_DIAMETER_M = 0.25
DEFAULT_THETA_MIN_DEG = -45.0

MODEL_NOTE_LINES: tuple[str, ...] = (
    "Model: reference_scaled thrust",
    "No CFD/BEMT/experiment yet",
    "Theta: moment-based hinge balance (V1)",
    OPENING_MOMENT_V1_MODEL_NOTE,
    ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE,
)

FOLDABLE_REPORT_FIGURE_NAMES: tuple[str, ...] = (
    "theta_deg_vs_throttle_by_variant.png",
    "effective_diameter_m_vs_throttle_by_variant.png",
    "foldable_thrust_n_vs_throttle_by_variant.png",
    "thrust_difference_percent_vs_throttle_by_variant.png",
    "fig_thrust_difference_normalized_250mm.png",
    "flight_startup_scores_by_variant.png",
)

FOLDABLE_REPORT_MARKDOWN_NAME = "foldable_figures_report.md"

SWEEP_THROTTLE_PLOTS: tuple[tuple[str, str, str, str], ...] = (
    (
        "theta_deg",
        "theta_deg_vs_throttle_by_variant.png",
        "Hinge angle vs throttle",
        "Geometry-dependent moment balance; variants may differ at equal throttle.",
    ),
    (
        "effective_diameter_m",
        "effective_diameter_m_vs_throttle_by_variant.png",
        "Effective diameter vs throttle",
        "Includes throttle=0 startup point at folded effective diameter.",
    ),
    (
        "foldable_thrust_n",
        "foldable_thrust_n_vs_throttle_by_variant.png",
        "Foldable thrust vs throttle",
        "Includes throttle=0 startup point with zero thrust.",
    ),
    (
        "thrust_difference_percent",
        "thrust_difference_percent_vs_throttle_by_variant.png",
        "Thrust difference vs throttle (APC reference_scaled)",
        "Relative to PyThrust fixed thrust at D_ref=0.254 m (APC reference).",
    ),
)

DECISION_SCORE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("startup_thrust_score", "Startup thrust"),
    ("active_window_diameter_growth_score", "Active window diameter growth"),
    ("flight_performance_score", "Flight performance"),
    ("takeoff_transition_score", "Takeoff transition"),
)


def _decision_row_score(row: Mapping[str, Any], column: str) -> float:
    if column == "active_window_diameter_growth_score":
        if column in row and row[column] not in ("", None):
            return float(row[column])
        return float(row["deployment_score"])
    return float(row[column])


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
                "rpm": float(row["rpm"]),
                "theta_deg": float(row["theta_deg"]),
                "effective_diameter_m": float(row["effective_diameter_m"]),
                "foldable_thrust_n": float(row["foldable_thrust_n"]),
                "fixed_thrust_n": float(row["fixed_thrust_n"]),
                "thrust_difference_percent": float(row["thrust_difference_percent"]),
                "compactness_ratio": float(row["compactness_ratio"]),
            }
            for row in reader
        ]


def thrust_difference_normalized_250mm(
    fixed_thrust_n: float,
    effective_diameter_m: float,
    *,
    reference_diameter_m: float = PROJECT_OPEN_DIAMETER_M,
    eta_hinge: float = 1.0,
    eta_profile: float = 1.0,
) -> float:
    """Proje açık çapına (0.25 m) göre normalize edilmiş itki farkı (%)."""
    if fixed_thrust_n <= 0.0:
        return 0.0
    ratio = effective_diameter_m / reference_diameter_m
    foldable_thrust_n = fixed_thrust_n * (ratio**4) * eta_hinge * eta_profile
    return (foldable_thrust_n - fixed_thrust_n) / fixed_thrust_n * 100.0


def enrich_sweep_rows_for_plots(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    theta_min_deg: float = DEFAULT_THETA_MIN_DEG,
    open_diameter_m: float = PROJECT_OPEN_DIAMETER_M,
    eta_hinge: float = 1.0,
    eta_profile: float = 1.0,
) -> List[Dict[str, Any]]:
    """Throttle=0 başlangıç noktası ve normalize itki farkını ekle."""
    grouped = _group_sweep_by_variant(sweep_rows)
    enriched: List[Dict[str, Any]] = []

    for variant_id in sorted(grouped):
        rows = grouped[variant_id]
        compactness_ratio = float(rows[0]["compactness_ratio"])
        folded_diameter_m = compactness_ratio * open_diameter_m
        has_zero_throttle = any(abs(float(row["throttle"])) <= 1e-9 for row in rows)

        if not has_zero_throttle:
            enriched.append(
                {
                    "variant_id": variant_id,
                    "throttle": 0.0,
                    "rpm": 0.0,
                    "theta_deg": theta_min_deg,
                    "effective_diameter_m": folded_diameter_m,
                    "foldable_thrust_n": 0.0,
                    "fixed_thrust_n": 0.0,
                    "thrust_difference_percent": 0.0,
                    "compactness_ratio": compactness_ratio,
                    "thrust_difference_normalized_250mm": 0.0,
                }
            )

        for row in rows:
            payload = dict(row)
            payload["thrust_difference_normalized_250mm"] = (
                thrust_difference_normalized_250mm(
                    float(payload["fixed_thrust_n"]),
                    float(payload["effective_diameter_m"]),
                    reference_diameter_m=open_diameter_m,
                    eta_hinge=eta_hinge,
                    eta_profile=eta_profile,
                )
            )
            enriched.append(payload)

    return enriched


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


def _theta_curves_overlap(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> bool:
    if len(grouped) <= 1:
        return True
    variant_ids = sorted(grouped)
    reference = [
        (float(row["throttle"]), float(row["theta_deg"]))
        for row in grouped[variant_ids[0]]
    ]
    for variant_id in variant_ids[1:]:
        pairs = [
            (float(row["throttle"]), float(row["theta_deg"]))
            for row in grouped[variant_id]
        ]
        if len(pairs) != len(reference):
            return False
        for ref_pair, pair in zip(reference, pairs):
            if abs(ref_pair[0] - pair[0]) > 1e-9 or abs(ref_pair[1] - pair[1]) > 1e-9:
                return False
    return True


def _add_model_note_to_figure(
    fig: plt.Figure,
    *,
    subtitle: str = "",
    extra_notes: Sequence[str] = (),
) -> None:
    note_lines = list(MODEL_NOTE_LINES)
    if subtitle:
        note_lines.insert(0, subtitle)
    note_lines.extend(extra_notes)
    fig.text(
        0.01,
        0.01,
        " | ".join(note_lines),
        ha="left",
        va="bottom",
        fontsize=7,
        color="0.35",
        wrap=True,
    )


def read_design_variant_decision_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Karar matrisi CSV dosyasını oku."""
    decision_path = Path(path)
    with decision_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {decision_path}")
        return [dict(row) for row in reader]


def plot_theta_vs_throttle(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    output_path: str | Path,
    subtitle: str,
) -> Path:
    """Hinge açısı grafiği; varyantlar örtüşüyorsa tek temsil çizgi."""
    grouped = _group_sweep_by_variant(sweep_rows)
    figure_path = Path(output_path)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axis = plt.subplots(figsize=(8, 5))
    overlap = _theta_curves_overlap(grouped)

    if overlap:
        rows = grouped[sorted(grouped)[0]]
        throttles = [float(row["throttle"]) for row in rows]
        values = [float(row["theta_deg"]) for row in rows]
        axis.plot(
            throttles,
            values,
            marker="o",
            label="All variants (shared kinematics)",
            color="tab:blue",
        )
        title = "Hinge angle vs throttle (shared kinematics)"
        note = "Same kinematics curve for all variants at equal throttle"
    else:
        for variant_id in sorted(grouped):
            rows = grouped[variant_id]
            throttles = [float(row["throttle"]) for row in rows]
            values = [float(row["theta_deg"]) for row in rows]
            axis.plot(throttles, values, marker="o", label=_variant_label(variant_id))
        title = "Hinge angle vs throttle by variant"
        note = ""

    axis.set_xlabel("Throttle")
    axis.set_ylabel("theta_deg")
    axis.set_title(title)
    axis.grid(True, linestyle="--", alpha=0.4)
    axis.legend(fontsize=8)
    _add_model_note_to_figure(fig, subtitle=subtitle, extra_notes=[note] if note else ())
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def plot_sweep_metric_vs_throttle(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    y_column: str,
    title: str,
    output_path: str | Path,
    ylabel: str | None = None,
    subtitle: str = "",
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
    _add_model_note_to_figure(fig, subtitle=subtitle)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.16)
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
        values = [_decision_row_score(row, column) for row in decision_rows]
        axis.bar(offsets, values, width=bar_width, label=legend_label)

    axis.set_xticks(x_positions)
    axis.set_xticklabels(labels)
    axis.set_xlabel("Variant")
    axis.set_ylabel("Normalized score")
    axis.set_ylim(0.0, 1.05)
    axis.set_title("Flight-startup decision scores by variant")
    axis.grid(True, axis="y", linestyle="--", alpha=0.4)
    axis.legend()
    _add_model_note_to_figure(
        fig,
        subtitle=ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE,
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def write_figure_report_markdown(
    figures_dir: str | Path,
    *,
    figure_captions: Sequence[tuple[str, str]],
) -> Path:
    """Üretilen grafikler için kısa markdown özet dosyası yaz."""
    output_dir = Path(figures_dir)
    report_path = output_dir / FOLDABLE_REPORT_MARKDOWN_NAME
    lines = [
        "# Foldable Report Figures",
        "",
        "## Model notes",
        "",
    ]
    for note in MODEL_NOTE_LINES:
        lines.append(f"- {note}")
    lines.extend(["", "## Figures", ""])
    for filename, caption in figure_captions:
        lines.append(f"### `{filename}`")
        lines.append("")
        lines.append(caption)
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def generate_sweep_figures(
    sweep_csv_path: str | Path,
    figures_dir: str | Path,
    *,
    theta_min_deg: float = DEFAULT_THETA_MIN_DEG,
    open_diameter_m: float = PROJECT_OPEN_DIAMETER_M,
) -> List[Path]:
    """Sweep CSV'den throttle tabanlı grafikleri üret."""
    sweep_rows = enrich_sweep_rows_for_plots(
        read_sweep_csv_for_plots(sweep_csv_path),
        theta_min_deg=theta_min_deg,
        open_diameter_m=open_diameter_m,
    )
    output_dir = Path(figures_dir)
    written: List[Path] = []

    for y_column, filename, title, subtitle in SWEEP_THROTTLE_PLOTS:
        output_path = output_dir / filename
        if y_column == "theta_deg":
            written.append(
                plot_theta_vs_throttle(
                    sweep_rows,
                    output_path=output_path,
                    subtitle=subtitle,
                )
            )
        else:
            written.append(
                plot_sweep_metric_vs_throttle(
                    sweep_rows,
                    y_column=y_column,
                    title=title,
                    output_path=output_path,
                    subtitle=subtitle,
                )
            )

    written.append(
        plot_sweep_metric_vs_throttle(
            sweep_rows,
            y_column="thrust_difference_normalized_250mm",
            title="Normalized thrust difference vs throttle (D_ref = 0.25 m)",
            output_path=output_dir / "fig_thrust_difference_normalized_250mm.png",
            ylabel="Thrust difference (%)",
            subtitle="Foldable loss relative to project open diameter 0.25 m, not APC 0.254 m.",
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
        output_path=Path(figures_dir) / "flight_startup_scores_by_variant.png",
    )


def _figure_captions() -> List[tuple[str, str]]:
    captions = [
        (filename, subtitle)
        for _, filename, _, subtitle in SWEEP_THROTTLE_PLOTS
    ]
    captions.append(
        (
            "fig_thrust_difference_normalized_250mm.png",
            "Foldable thrust loss scaled with D_ref = 0.25 m project diameter.",
        )
    )
    captions.append(
        (
            "flight_startup_scores_by_variant.png",
            f"Preferred label: active_window_diameter_growth_score "
            f"(deployment_score kept in CSV). {ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE}",
        )
    )
    return captions


def generate_foldable_report_figures(
    *,
    sweep_csv_path: str | Path,
    summary_csv_path: str | Path,
    decision_csv_path: str | Path,
    figures_dir: str | Path,
    theta_min_deg: float = DEFAULT_THETA_MIN_DEG,
    open_diameter_m: float = PROJECT_OPEN_DIAMETER_M,
) -> List[Path]:
    """Tüm foldable rapor grafiklerini ve markdown özetini üret."""
    del summary_csv_path  # reserved for future summary overlays
    output_dir = Path(figures_dir)
    written = generate_sweep_figures(
        sweep_csv_path,
        output_dir,
        theta_min_deg=theta_min_deg,
        open_diameter_m=open_diameter_m,
    )
    written.append(generate_decision_figure(decision_csv_path, output_dir))
    written.append(write_figure_report_markdown(output_dir, figure_captions=_figure_captions()))
    return written
