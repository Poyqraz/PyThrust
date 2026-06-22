"""Tasarım varyantı sweep özet metrikleri."""

from __future__ import annotations

import csv
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

DESIGN_VARIANT_SUMMARY_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "folded_diameter_ratio",
    "compactness_gain_percent",
    "thrust_diff_at_02",
    "thrust_diff_at_06",
    "thrust_diff_at_10",
    "mean_thrust_difference_percent",
    "min_effective_diameter_m",
    "max_effective_diameter_m",
    "score_simple",
    "model_note",
)

DESIGN_VARIANT_SUMMARY_MODEL_NOTE = (
    "Summary from design_variant_sweep.csv; folded_diameter_ratio = "
    "folded_effective_diameter / open_diameter (lower is more compact); "
    "compactness_gain_percent = (1 - folded_diameter_ratio) * 100; "
    "score_simple = compactness_gain_percent + mean_thrust_difference_percent; "
    "min/max effective_diameter_m feed active_window_diameter_growth_score in "
    "decision matrix (deployment_score kept for backward compatibility); "
    "active_window_diameter_growth_score measures observed diameter growth over "
    "sampled throttle values, not total stowed-to-open geometric deployment"
)

THROTTLE_TOLERANCE = 1e-6
KEY_THROTTLES: tuple[tuple[str, float], ...] = (
    ("thrust_diff_at_02", 0.2),
    ("thrust_diff_at_06", 0.6),
    ("thrust_diff_at_10", 1.0),
)


@dataclass(frozen=True)
class DesignVariantSummaryRow:
    """Varyant başına özet karşılaştırma satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    folded_diameter_ratio: float
    compactness_gain_percent: float
    thrust_diff_at_02: float
    thrust_diff_at_06: float
    thrust_diff_at_10: float
    mean_thrust_difference_percent: float
    min_effective_diameter_m: float
    max_effective_diameter_m: float
    score_simple: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compactness_gain_percent(folded_diameter_ratio: float) -> float:
    """Katlı çapın açık çapa göre yüzde küçülmesi (daha yüksek = daha kompakt)."""
    return (1.0 - folded_diameter_ratio) * 100.0


def score_simple(
    compactness_gain_percent_value: float,
    mean_thrust_difference_percent: float,
) -> float:
    """Basit denge skoru: kompaktlık kazancı + ortalama itki farkı (negatif)."""
    return compactness_gain_percent_value + mean_thrust_difference_percent


def _parse_sweep_row(row: Mapping[str, str]) -> Dict[str, Any]:
    return {
        "variant_id": row["variant_id"],
        "root_ratio": int(row["root_ratio"]),
        "tip_ratio": int(row["tip_ratio"]),
        "throttle": float(row["throttle"]),
        "effective_diameter_m": float(row["effective_diameter_m"]),
        "thrust_difference_percent": float(row["thrust_difference_percent"]),
        "compactness_ratio": float(row["compactness_ratio"]),
    }


def read_design_variant_sweep_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Sweep CSV dosyasını oku ve satır sözlükleri döndür."""
    sweep_path = Path(path)
    with sweep_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {sweep_path}")
        return [_parse_sweep_row(row) for row in reader]


def _thrust_diff_at_throttle(
    rows: Sequence[Mapping[str, Any]],
    throttle: float,
) -> float:
    for row in rows:
        if abs(float(row["throttle"]) - throttle) <= THROTTLE_TOLERANCE:
            return float(row["thrust_difference_percent"])
    raise ValueError(f"No sweep row found for throttle={throttle}")


def summarize_variant_rows(
    variant_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> DesignVariantSummaryRow:
    """Tek varyanta ait sweep satırlarından özet üret."""
    if not rows:
        raise ValueError(f"No sweep rows for variant '{variant_id}'")

    root_ratio = int(rows[0]["root_ratio"])
    tip_ratio = int(rows[0]["tip_ratio"])
    folded_diameter_ratio = float(rows[0]["compactness_ratio"])
    gain = compactness_gain_percent(folded_diameter_ratio)

    thrust_values = [float(row["thrust_difference_percent"]) for row in rows]
    mean_thrust = statistics.fmean(thrust_values)

    diameters = [float(row["effective_diameter_m"]) for row in rows]
    thrust_at = {
        field: _thrust_diff_at_throttle(rows, throttle)
        for field, throttle in KEY_THROTTLES
    }

    return DesignVariantSummaryRow(
        variant_id=variant_id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        folded_diameter_ratio=folded_diameter_ratio,
        compactness_gain_percent=gain,
        thrust_diff_at_02=thrust_at["thrust_diff_at_02"],
        thrust_diff_at_06=thrust_at["thrust_diff_at_06"],
        thrust_diff_at_10=thrust_at["thrust_diff_at_10"],
        mean_thrust_difference_percent=mean_thrust,
        min_effective_diameter_m=min(diameters),
        max_effective_diameter_m=max(diameters),
        score_simple=score_simple(gain, mean_thrust),
        model_note=model_note,
    )


def summarize_design_variants(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> List[DesignVariantSummaryRow]:
    """Sweep satırlarını varyant başına gruplayıp özet tablo üret."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in sweep_rows:
        variant_id = str(row["variant_id"])
        grouped.setdefault(variant_id, []).append(dict(row))

    return [
        summarize_variant_rows(variant_id, grouped[variant_id], model_note=model_note)
        for variant_id in sorted(grouped)
    ]


def summarize_design_variants_from_csv(
    sweep_csv_path: str | Path,
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> List[DesignVariantSummaryRow]:
    """Sweep CSV dosyasından özet tablo üret."""
    return summarize_design_variants(
        read_design_variant_sweep_csv(sweep_csv_path),
        model_note=model_note,
    )


def validate_design_variant_summary_columns(columns: Sequence[str]) -> List[str]:
    """Özet CSV kolonlarını doğrula; eksikleri döndür."""
    return [col for col in DESIGN_VARIANT_SUMMARY_COLUMNS if col not in columns]


def write_design_variant_summary_csv(
    path: str | Path,
    rows: Sequence[DesignVariantSummaryRow],
    *,
    columns: Sequence[str] = DESIGN_VARIANT_SUMMARY_COLUMNS,
) -> Path:
    """Özet satırlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_design_variant_summary_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            payload = row.to_dict()
            writer.writerow({key: payload[key] for key in columns})

    return output_path
