"""Tasarım varyantı ağırlıklı karar skorları."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

DESIGN_VARIANT_DECISION_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "compactness_gain_percent",
    "mean_thrust_difference_percent",
    "performance_score",
    "compactness_score",
    "balanced_score",
    "flight_priority_score",
    "ground_priority_score",
    "recommendation_note",
)

RECOMMENDATION_COMPACT = "compact"
RECOMMENDATION_BALANCED = "balanced_candidate"
RECOMMENDATION_FLIGHT = "flight_priority"
RECOMMENDATION_NOT = "not_recommended"

VALID_RECOMMENDATIONS: frozenset[str] = frozenset(
    {
        RECOMMENDATION_COMPACT,
        RECOMMENDATION_BALANCED,
        RECOMMENDATION_FLIGHT,
        RECOMMENDATION_NOT,
    }
)

NOT_RECOMMENDED_THRESHOLD = 0.2
FALLBACK_RECOMMENDATION_THRESHOLD = 0.35

BALANCED_COMPACTNESS_WEIGHT = 0.5
BALANCED_PERFORMANCE_WEIGHT = 0.5
FLIGHT_COMPACTNESS_WEIGHT = 0.3
FLIGHT_PERFORMANCE_WEIGHT = 0.7
GROUND_COMPACTNESS_WEIGHT = 0.7
GROUND_PERFORMANCE_WEIGHT = 0.3


@dataclass(frozen=True)
class DesignVariantDecisionRow:
    """Varyant başına ağırlıklı karar skoru satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    compactness_gain_percent: float
    mean_thrust_difference_percent: float
    performance_score: float
    compactness_score: float
    balanced_score: float
    flight_priority_score: float
    ground_priority_score: float
    recommendation_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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


def thrust_preservation_value(mean_thrust_difference_percent: float) -> float:
    """İtki korunumu: ortalama kayıp yüzdesi sıfıra ne kadar yakınsa o kadar iyi."""
    return mean_thrust_difference_percent


def weighted_score(
    compactness_score: float,
    performance_score: float,
    *,
    compactness_weight: float,
    performance_weight: float,
) -> float:
    """Ağırlıklı birleşik skor."""
    return (
        compactness_weight * compactness_score
        + performance_weight * performance_score
    )


def balanced_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=BALANCED_COMPACTNESS_WEIGHT,
        performance_weight=BALANCED_PERFORMANCE_WEIGHT,
    )


def flight_priority_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=FLIGHT_COMPACTNESS_WEIGHT,
        performance_weight=FLIGHT_PERFORMANCE_WEIGHT,
    )


def ground_priority_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=GROUND_COMPACTNESS_WEIGHT,
        performance_weight=GROUND_PERFORMANCE_WEIGHT,
    )


def _parse_summary_row(row: Mapping[str, str]) -> Dict[str, Any]:
    return {
        "variant_id": row["variant_id"],
        "root_ratio": int(row["root_ratio"]),
        "tip_ratio": int(row["tip_ratio"]),
        "compactness_gain_percent": float(row["compactness_gain_percent"]),
        "mean_thrust_difference_percent": float(row["mean_thrust_difference_percent"]),
    }


def read_design_variant_summary_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Özet CSV dosyasını oku."""
    summary_path = Path(path)
    with summary_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {summary_path}")
        return [_parse_summary_row(row) for row in reader]


def _argmax_variant(
    rows: Sequence[DesignVariantDecisionRow],
    attr: str,
) -> str:
    best = max(rows, key=lambda row: getattr(row, attr))
    return best.variant_id


def classify_recommendation(
    row: DesignVariantDecisionRow,
    *,
    compact_winner: str,
    balanced_winner: str,
    flight_winner: str,
) -> str:
    """Varyant için öneri sınıfı üret."""
    peak = max(
        row.balanced_score,
        row.flight_priority_score,
        row.ground_priority_score,
    )
    if peak < NOT_RECOMMENDED_THRESHOLD:
        return RECOMMENDATION_NOT

    if row.variant_id == compact_winner:
        return RECOMMENDATION_COMPACT
    if row.variant_id == flight_winner:
        return RECOMMENDATION_FLIGHT
    if row.variant_id == balanced_winner:
        return RECOMMENDATION_BALANCED

    if row.balanced_score >= FALLBACK_RECOMMENDATION_THRESHOLD:
        return RECOMMENDATION_BALANCED
    return RECOMMENDATION_NOT


def build_decision_matrix(
    summary_rows: Sequence[Mapping[str, Any]],
) -> List[DesignVariantDecisionRow]:
    """Özet satırlarından ağırlıklı karar matrisi üret."""
    if not summary_rows:
        return []

    compactness_values = [
        float(row["compactness_gain_percent"]) for row in summary_rows
    ]
    preservation_values = [
        thrust_preservation_value(float(row["mean_thrust_difference_percent"]))
        for row in summary_rows
    ]

    compactness_scores = min_max_normalize(compactness_values)
    performance_scores = min_max_normalize(preservation_values)

    preliminary: List[DesignVariantDecisionRow] = []
    for index, summary in enumerate(summary_rows):
        compactness_score = compactness_scores[index]
        performance_score = performance_scores[index]
        preliminary.append(
            DesignVariantDecisionRow(
                variant_id=str(summary["variant_id"]),
                root_ratio=int(summary["root_ratio"]),
                tip_ratio=int(summary["tip_ratio"]),
                compactness_gain_percent=float(summary["compactness_gain_percent"]),
                mean_thrust_difference_percent=float(
                    summary["mean_thrust_difference_percent"]
                ),
                performance_score=performance_score,
                compactness_score=compactness_score,
                balanced_score=balanced_score(compactness_score, performance_score),
                flight_priority_score=flight_priority_score(
                    compactness_score,
                    performance_score,
                ),
                ground_priority_score=ground_priority_score(
                    compactness_score,
                    performance_score,
                ),
                recommendation_note=RECOMMENDATION_NOT,
            )
        )

    compact_winner = _argmax_variant(preliminary, "ground_priority_score")
    flight_winner = _argmax_variant(preliminary, "flight_priority_score")
    remaining = [
        row
        for row in preliminary
        if row.variant_id not in {compact_winner, flight_winner}
    ]
    balanced_winner = (
        _argmax_variant(remaining, "balanced_score")
        if remaining
        else compact_winner
    )

    return [
        DesignVariantDecisionRow(
            variant_id=row.variant_id,
            root_ratio=row.root_ratio,
            tip_ratio=row.tip_ratio,
            compactness_gain_percent=row.compactness_gain_percent,
            mean_thrust_difference_percent=row.mean_thrust_difference_percent,
            performance_score=row.performance_score,
            compactness_score=row.compactness_score,
            balanced_score=row.balanced_score,
            flight_priority_score=row.flight_priority_score,
            ground_priority_score=row.ground_priority_score,
            recommendation_note=classify_recommendation(
                row,
                compact_winner=compact_winner,
                balanced_winner=balanced_winner,
                flight_winner=flight_winner,
            ),
        )
        for row in preliminary
    ]


def build_decision_matrix_from_csv(summary_csv_path: str | Path) -> List[DesignVariantDecisionRow]:
    """Özet CSV dosyasından karar matrisi üret."""
    return build_decision_matrix(read_design_variant_summary_csv(summary_csv_path))


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
