"""Tasarım varyantı uçuş-başlangıcı karar skorları."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .summary import THROTTLE_TOLERANCE, read_design_variant_sweep_csv

ACTIVE_WINDOW_DIAMETER_GROWTH_SCORE_NOTE = (
    "active_window_diameter_growth_score measures observed diameter growth "
    "over sampled throttle values, not total stowed-to-open geometric deployment."
)

DESIGN_VARIANT_DECISION_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "folded_diameter_ratio",
    "compactness_gain_percent",
    "startup_thrust_score",
    "flight_performance_score",
    "deployment_score",
    "active_window_diameter_growth_score",
    "takeoff_transition_score",
    "recommendation_note",
)

RECOMMENDATION_TAKEOFF = "best_takeoff_transition"
RECOMMENDATION_FLIGHT = "best_flight_performance"
RECOMMENDATION_STARTUP = "best_startup_thrust"
RECOMMENDATION_DEPLOYMENT = "best_deployment"
RECOMMENDATION_BALANCED = "balanced_candidate"
RECOMMENDATION_NOT = "not_recommended"

VALID_RECOMMENDATIONS: frozenset[str] = frozenset(
    {
        RECOMMENDATION_TAKEOFF,
        RECOMMENDATION_FLIGHT,
        RECOMMENDATION_STARTUP,
        RECOMMENDATION_DEPLOYMENT,
        RECOMMENDATION_BALANCED,
        RECOMMENDATION_NOT,
    }
)

NOT_RECOMMENDED_THRESHOLD = 0.2
FALLBACK_RECOMMENDATION_THRESHOLD = 0.35

TAKEOFF_STARTUP_WEIGHT = 0.35
TAKEOFF_DEPLOYMENT_WEIGHT = 0.35
TAKEOFF_FLIGHT_WEIGHT = 0.30

STARTUP_THRUST_AT_02_WEIGHT = 0.6
STARTUP_THRUST_AT_04_WEIGHT = 0.4

FLIGHT_MEAN_WEIGHT = 0.5
FLIGHT_AT_10_WEIGHT = 0.5


@dataclass(frozen=True)
class DesignVariantDecisionRow:
    """Varyant başına uçuş-başlangıcı karar skoru satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    folded_diameter_ratio: float
    compactness_gain_percent: float
    startup_thrust_score: float
    flight_performance_score: float
    deployment_score: float
    takeoff_transition_score: float
    recommendation_note: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["active_window_diameter_growth_score"] = self.deployment_score
        return data


def min_max_normalize(values: Sequence[float]) -> List[float]:
    """Değerleri [0, 1] aralığına ölçekle; yüksek ham değer = 1.0."""
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [1.0 for _ in values]
    span = vmax - vmin
    return [(value - vmin) / span for value in values]


def thrust_preservation_value(thrust_difference_percent: float) -> float:
    """İtki korunumu: kayıp yüzdesi sıfıra ne kadar yakınsa o kadar iyi."""
    return thrust_difference_percent


def startup_thrust_raw(
    thrust_diff_at_02: float,
    thrust_diff_at_04: Optional[float] = None,
) -> float:
    """Düşük throttle itki korunumu (0.2 ve varsa 0.4)."""
    if thrust_diff_at_04 is None:
        return thrust_preservation_value(thrust_diff_at_02)
    return (
        STARTUP_THRUST_AT_02_WEIGHT * thrust_preservation_value(thrust_diff_at_02)
        + STARTUP_THRUST_AT_04_WEIGHT * thrust_preservation_value(thrust_diff_at_04)
    )


def flight_performance_raw(
    mean_thrust_difference_percent: float,
    thrust_diff_at_10: float,
) -> float:
    """Uçuş performansı: ortalama itki korunumu + tam gaz noktası."""
    return (
        FLIGHT_MEAN_WEIGHT * thrust_preservation_value(mean_thrust_difference_percent)
        + FLIGHT_AT_10_WEIGHT * thrust_preservation_value(thrust_diff_at_10)
    )


def deployment_raw(
    min_effective_diameter_m: float,
    max_effective_diameter_m: float,
) -> float:
    """Örneklenen throttle penceresinde gözlenen efektif çap büyümesi.

    ``active_window_diameter_growth_raw = (D_max - D_min) / D_max`` where
    ``D_min``/``D_max`` are min/max ``effective_diameter_m`` over the sampled
    throttle points. This is **not** total stowed-to-open geometric deployment.
    """
    if max_effective_diameter_m <= 0.0:
        return 0.0
    growth_m = max_effective_diameter_m - min_effective_diameter_m
    return max(growth_m / max_effective_diameter_m, 0.0)


def takeoff_transition_score(
    startup_thrust_score: float,
    deployment_score: float,
    flight_performance_score: float,
) -> float:
    """Kalkış geçiş skoru: startup + deployment + flight performance."""
    return (
        TAKEOFF_STARTUP_WEIGHT * startup_thrust_score
        + TAKEOFF_DEPLOYMENT_WEIGHT * deployment_score
        + TAKEOFF_FLIGHT_WEIGHT * flight_performance_score
    )


def _parse_summary_row(row: Mapping[str, str]) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {
        "variant_id": row["variant_id"],
        "root_ratio": int(row["root_ratio"]),
        "tip_ratio": int(row["tip_ratio"]),
        "folded_diameter_ratio": float(row["folded_diameter_ratio"]),
        "compactness_gain_percent": float(row["compactness_gain_percent"]),
        "thrust_diff_at_02": float(row["thrust_diff_at_02"]),
        "thrust_diff_at_10": float(row["thrust_diff_at_10"]),
        "mean_thrust_difference_percent": float(row["mean_thrust_difference_percent"]),
        "min_effective_diameter_m": float(row["min_effective_diameter_m"]),
        "max_effective_diameter_m": float(row["max_effective_diameter_m"]),
        "thrust_diff_at_04": None,
    }
    if "thrust_diff_at_04" in row and row["thrust_diff_at_04"]:
        parsed["thrust_diff_at_04"] = float(row["thrust_diff_at_04"])
    return parsed


def read_design_variant_summary_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Özet CSV dosyasını oku."""
    summary_path = Path(path)
    with summary_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {summary_path}")
        return [_parse_summary_row(row) for row in reader]


def _thrust_diff_at_throttle(
    rows: Sequence[Mapping[str, Any]],
    throttle: float,
) -> Optional[float]:
    for row in rows:
        if abs(float(row["throttle"]) - throttle) <= THROTTLE_TOLERANCE:
            return float(row["thrust_difference_percent"])
    return None


def enrich_summary_with_sweep_throttles(
    summary_rows: Sequence[Mapping[str, Any]],
    sweep_csv_path: str | Path,
) -> List[Dict[str, Any]]:
    """Özet satırlarına sweep'ten eksik düşük throttle noktalarını ekle."""
    sweep_path = Path(sweep_csv_path)
    if not sweep_path.is_file():
        return [dict(row) for row in summary_rows]

    sweep_rows = read_design_variant_sweep_csv(sweep_path)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in sweep_rows:
        variant_id = str(row["variant_id"])
        grouped.setdefault(variant_id, []).append(dict(row))

    enriched: List[Dict[str, Any]] = []
    for summary in summary_rows:
        payload = dict(summary)
        variant_id = str(payload["variant_id"])
        if payload.get("thrust_diff_at_04") is None and variant_id in grouped:
            payload["thrust_diff_at_04"] = _thrust_diff_at_throttle(
                grouped[variant_id],
                0.4,
            )
        enriched.append(payload)
    return enriched


def _argmax_variant(
    rows: Sequence[DesignVariantDecisionRow],
    attr: str,
) -> str:
    best = max(rows, key=lambda row: getattr(row, attr))
    return best.variant_id


def classify_recommendation(
    row: DesignVariantDecisionRow,
    *,
    takeoff_winner: str,
    flight_winner: str,
    startup_winner: str,
    deployment_winner: str,
) -> str:
    """Varyant için öneri sınıfı üret."""
    if row.takeoff_transition_score < NOT_RECOMMENDED_THRESHOLD:
        return RECOMMENDATION_NOT

    if row.variant_id == takeoff_winner:
        return RECOMMENDATION_TAKEOFF
    if row.variant_id == flight_winner:
        return RECOMMENDATION_FLIGHT
    if row.variant_id == startup_winner:
        return RECOMMENDATION_STARTUP
    if row.variant_id == deployment_winner:
        return RECOMMENDATION_DEPLOYMENT

    if row.takeoff_transition_score >= FALLBACK_RECOMMENDATION_THRESHOLD:
        return RECOMMENDATION_BALANCED
    return RECOMMENDATION_NOT


def build_decision_matrix(
    summary_rows: Sequence[Mapping[str, Any]],
) -> List[DesignVariantDecisionRow]:
    """Özet satırlarından uçuş-başlangıcı karar matrisi üret."""
    if not summary_rows:
        return []

    startup_raw_values = [
        startup_thrust_raw(
            float(row["thrust_diff_at_02"]),
            row.get("thrust_diff_at_04"),
        )
        for row in summary_rows
    ]
    flight_raw_values = [
        flight_performance_raw(
            float(row["mean_thrust_difference_percent"]),
            float(row["thrust_diff_at_10"]),
        )
        for row in summary_rows
    ]
    deployment_raw_values = [
        deployment_raw(
            float(row["min_effective_diameter_m"]),
            float(row["max_effective_diameter_m"]),
        )
        for row in summary_rows
    ]

    startup_scores = min_max_normalize(startup_raw_values)
    flight_scores = min_max_normalize(flight_raw_values)
    deployment_scores = min_max_normalize(deployment_raw_values)

    preliminary: List[DesignVariantDecisionRow] = []
    for index, summary in enumerate(summary_rows):
        startup_score = startup_scores[index]
        flight_score = flight_scores[index]
        deployment_score = deployment_scores[index]
        preliminary.append(
            DesignVariantDecisionRow(
                variant_id=str(summary["variant_id"]),
                root_ratio=int(summary["root_ratio"]),
                tip_ratio=int(summary["tip_ratio"]),
                folded_diameter_ratio=float(summary["folded_diameter_ratio"]),
                compactness_gain_percent=float(summary["compactness_gain_percent"]),
                startup_thrust_score=startup_score,
                flight_performance_score=flight_score,
                deployment_score=deployment_score,
                takeoff_transition_score=takeoff_transition_score(
                    startup_score,
                    deployment_score,
                    flight_score,
                ),
                recommendation_note=RECOMMENDATION_NOT,
            )
        )

    takeoff_winner = _argmax_variant(preliminary, "takeoff_transition_score")
    flight_winner = _argmax_variant(preliminary, "flight_performance_score")
    startup_winner = _argmax_variant(preliminary, "startup_thrust_score")
    deployment_winner = _argmax_variant(preliminary, "deployment_score")

    return [
        DesignVariantDecisionRow(
            variant_id=row.variant_id,
            root_ratio=row.root_ratio,
            tip_ratio=row.tip_ratio,
            folded_diameter_ratio=row.folded_diameter_ratio,
            compactness_gain_percent=row.compactness_gain_percent,
            startup_thrust_score=row.startup_thrust_score,
            flight_performance_score=row.flight_performance_score,
            deployment_score=row.deployment_score,
            takeoff_transition_score=row.takeoff_transition_score,
            recommendation_note=classify_recommendation(
                row,
                takeoff_winner=takeoff_winner,
                flight_winner=flight_winner,
                startup_winner=startup_winner,
                deployment_winner=deployment_winner,
            ),
        )
        for row in preliminary
    ]


def build_decision_matrix_from_csv(
    summary_csv_path: str | Path,
    *,
    sweep_csv_path: str | Path | None = None,
) -> List[DesignVariantDecisionRow]:
    """Özet CSV dosyasından karar matrisi üret."""
    summary_path = Path(summary_csv_path)
    if sweep_csv_path is None:
        sweep_csv_path = summary_path.parent / "design_variant_sweep.csv"
    summary_rows = enrich_summary_with_sweep_throttles(
        read_design_variant_summary_csv(summary_path),
        sweep_csv_path,
    )
    return build_decision_matrix(summary_rows)


def validate_design_variant_decision_columns(columns: Sequence[str]) -> List[str]:
    """Karar matrisi kolonlarını doğrula; eksikleri döndür."""
    return [col for col in DESIGN_VARIANT_DECISION_COLUMNS if col not in columns]


def write_design_variant_decision_csv(
    path: str | Path,
    rows: Sequence[DesignVariantDecisionRow],
    *,
    columns: Sequence[str] = DESIGN_VARIANT_DECISION_COLUMNS,
) -> Path:
    """Karar matrisi satırlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_design_variant_decision_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            payload = row.to_dict()
            writer.writerow({key: payload[key] for key in columns})

    return output_path
