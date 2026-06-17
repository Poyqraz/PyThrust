"""Design variant decision matrix tests."""

from pathlib import Path

import pytest

from pythrust.foldable.decision import (
    DESIGN_VARIANT_DECISION_COLUMNS,
    RECOMMENDATION_BALANCED,
    RECOMMENDATION_FLIGHT,
    RECOMMENDATION_NOT,
    RECOMMENDATION_STOWED,
    VALID_RECOMMENDATIONS,
    balanced_score,
    build_decision_matrix_from_csv,
    flight_priority_score,
    min_max_normalize,
    stowed_compactness_score,
    stowed_priority_score,
    validate_design_variant_decision_columns,
    write_design_variant_decision_csv,
)
from pythrust.foldable.design_sweep import sweep_design_variants
from pythrust.foldable.models import load_config
from pythrust.foldable.summary import (
    summarize_design_variants_from_csv,
    write_design_variant_summary_csv,
)
from pythrust.foldable.validation import write_design_variant_sweep_csv
from pythrust.foldable.variants import DEFAULT_ROOT_TIP_RATIOS
from pythrust.propellers.database import PropellerDatabase


@pytest.fixture
def summary_csv(tmp_path):
    config = load_config("configs/foldable/TIP_HINGED_250_V01.json")
    db = PropellerDatabase()
    db.load(Path("data/propellers/apc_202602"), strict=False)
    prop_entry = db.get("APC_10x4.7SF")
    assert prop_entry is not None

    sweep_rows = sweep_design_variants(
        config,
        prop_entry,
        throttle_values=[0.2, 0.4, 0.6, 0.8, 1.0],
    )
    sweep_path = tmp_path / "design_variant_sweep.csv"
    write_design_variant_sweep_csv(sweep_path, sweep_rows)

    summary_rows = summarize_design_variants_from_csv(sweep_path)
    summary_path = tmp_path / "design_variant_summary.csv"
    write_design_variant_summary_csv(summary_path, summary_rows)
    return summary_path


def test_decision_columns_complete() -> None:
    assert validate_design_variant_decision_columns(DESIGN_VARIANT_DECISION_COLUMNS) == []


def test_decision_has_five_variants(summary_csv) -> None:
    rows = build_decision_matrix_from_csv(summary_csv)
    assert len(rows) == len(DEFAULT_ROOT_TIP_RATIOS)


def test_normalized_scores_in_unit_interval(summary_csv) -> None:
    rows = build_decision_matrix_from_csv(summary_csv)
    for row in rows:
        assert 0.0 <= row.compactness_score <= 1.0
        assert 0.0 <= row.performance_score <= 1.0
        assert 0.0 <= row.balanced_score <= 1.0
        assert 0.0 <= row.flight_priority_score <= 1.0
        assert 0.0 <= row.stowed_compactness_score <= 1.0
        assert 0.0 <= row.stowed_priority_score <= 1.0


def test_weighted_score_formulas() -> None:
    compactness_score = 0.8
    performance_score = 0.4
    assert balanced_score(compactness_score, performance_score) == pytest.approx(0.6)
    assert flight_priority_score(compactness_score, performance_score) == pytest.approx(
        0.48
    )
    assert stowed_compactness_score(compactness_score) == pytest.approx(0.8)
    assert stowed_priority_score(compactness_score) == pytest.approx(0.8)


def test_stowed_scores_ignore_thrust_preservation() -> None:
    compactness_score = 0.2
    assert stowed_compactness_score(compactness_score) == pytest.approx(0.2)
    assert stowed_priority_score(compactness_score) == pytest.approx(0.2)


def test_min_max_normalize_range() -> None:
    normalized = min_max_normalize([1.0, 2.0, 3.0, 4.0])
    assert normalized[0] == pytest.approx(0.0)
    assert normalized[-1] == pytest.approx(1.0)
    assert all(0.0 <= value <= 1.0 for value in normalized)


def test_recommendation_labels(summary_csv) -> None:
    rows = build_decision_matrix_from_csv(summary_csv)
    by_id = {row.variant_id: row for row in rows}
    notes = {row.recommendation_note for row in rows}
    assert notes.issubset(VALID_RECOMMENDATIONS)
    assert by_id["TIP_HINGED_250_RT65_35"].recommendation_note == RECOMMENDATION_STOWED
    assert by_id["TIP_HINGED_250_RT85_15"].recommendation_note == RECOMMENDATION_FLIGHT
    assert RECOMMENDATION_BALANCED in notes


def test_winners_match_expected_variants(summary_csv) -> None:
    rows = {row.variant_id: row for row in build_decision_matrix_from_csv(summary_csv)}
    assert rows["TIP_HINGED_250_RT65_35"].recommendation_note == RECOMMENDATION_STOWED
    assert rows["TIP_HINGED_250_RT85_15"].recommendation_note == RECOMMENDATION_FLIGHT


def test_decision_csv_columns(summary_csv, tmp_path) -> None:
    rows = build_decision_matrix_from_csv(summary_csv)
    output = tmp_path / "design_variant_decision_matrix.csv"
    write_design_variant_decision_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in DESIGN_VARIANT_DECISION_COLUMNS:
        assert col in content
    assert "ground_priority_score" not in content
    assert "stowed_compactness_score" not in content


def test_not_recommended_for_weak_variant() -> None:
    from pythrust.foldable.decision import build_decision_matrix

    rows = build_decision_matrix(
        [
            {
                "variant_id": "STRONG",
                "root_ratio": 65,
                "tip_ratio": 35,
                "compactness_gain_percent": 10.0,
                "mean_thrust_difference_percent": -11.0,
            },
            {
                "variant_id": "WEAK",
                "root_ratio": 50,
                "tip_ratio": 50,
                "compactness_gain_percent": 1.0,
                "mean_thrust_difference_percent": -40.0,
            },
        ]
    )
    weak = next(row for row in rows if row.variant_id == "WEAK")
    assert weak.recommendation_note == RECOMMENDATION_NOT
