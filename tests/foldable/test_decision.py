"""Design variant decision matrix tests."""

from pathlib import Path

import pytest

from pythrust.foldable.decision import (
    DESIGN_VARIANT_DECISION_COLUMNS,
    RECOMMENDATION_BALANCED,
    RECOMMENDATION_FLIGHT,
    RECOMMENDATION_NOT,
    RECOMMENDATION_TAKEOFF,
    VALID_RECOMMENDATIONS,
    build_decision_matrix,
    build_decision_matrix_from_csv,
    deployment_raw,
    flight_performance_raw,
    min_max_normalize,
    startup_thrust_raw,
    takeoff_transition_score,
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
    return summary_path, sweep_path


def test_decision_columns_complete() -> None:
    assert validate_design_variant_decision_columns(DESIGN_VARIANT_DECISION_COLUMNS) == []


def test_decision_has_five_variants(summary_csv) -> None:
    summary_path, sweep_path = summary_csv
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    assert len(rows) == len(DEFAULT_ROOT_TIP_RATIOS)


def test_flight_startup_scores_in_unit_interval(summary_csv) -> None:
    summary_path, sweep_path = summary_csv
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    for row in rows:
        assert 0.0 <= row.startup_thrust_score <= 1.0
        assert 0.0 <= row.flight_performance_score <= 1.0
        assert 0.0 <= row.deployment_score <= 1.0
        assert 0.0 <= row.takeoff_transition_score <= 1.0


def test_startup_uses_low_throttle_points() -> None:
    with_04 = startup_thrust_raw(-30.0, -20.0)
    without_04 = startup_thrust_raw(-30.0, None)
    assert with_04 > without_04


def test_takeoff_transition_weighted_sum() -> None:
    score = takeoff_transition_score(0.8, 0.6, 0.4)
    assert score == pytest.approx(0.35 * 0.8 + 0.35 * 0.6 + 0.30 * 0.4)


def test_flight_performance_raw_average() -> None:
    raw = flight_performance_raw(-12.0, -6.0)
    assert raw == pytest.approx(-9.0)


def test_deployment_raw_from_diameter_growth() -> None:
    raw = deployment_raw(0.22, 0.25)
    assert raw == pytest.approx(0.12)


def test_min_max_normalize_range() -> None:
    normalized = min_max_normalize([1.0, 2.0, 3.0, 4.0])
    assert normalized[0] == pytest.approx(0.0)
    assert normalized[-1] == pytest.approx(1.0)


def test_recommendation_labels(summary_csv) -> None:
    summary_path, sweep_path = summary_csv
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    notes = {row.recommendation_note for row in rows}
    assert notes.issubset(VALID_RECOMMENDATIONS)
    assert RECOMMENDATION_TAKEOFF in notes
    assert RECOMMENDATION_BALANCED in notes


def test_best_flight_performance_score(summary_csv) -> None:
    summary_path, sweep_path = summary_csv
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    best_flight = max(rows, key=lambda row: row.flight_performance_score)
    # Moment-based kinematics: longer tip segment opens more at equal RPM → better thrust.
    assert best_flight.variant_id == "TIP_HINGED_250_RT65_35"


def test_decision_csv_columns(summary_csv, tmp_path) -> None:
    summary_path, sweep_path = summary_csv
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    output = tmp_path / "design_variant_decision_matrix.csv"
    write_design_variant_decision_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in DESIGN_VARIANT_DECISION_COLUMNS:
        assert col in content
    for row in rows:
        assert row.deployment_score == row.to_dict()["active_window_diameter_growth_score"]
    assert "stowed_priority_score" not in content
    assert "ground_priority_score" not in content
    assert "compactness_score" not in content
    assert "balanced_score" not in content


def test_not_recommended_for_weak_variant() -> None:
    rows = build_decision_matrix(
        [
            {
                "variant_id": "STRONG",
                "root_ratio": 65,
                "tip_ratio": 35,
                "folded_diameter_ratio": 0.90,
                "compactness_gain_percent": 10.0,
                "thrust_diff_at_02": -20.0,
                "thrust_diff_at_04": -15.0,
                "thrust_diff_at_10": -6.0,
                "mean_thrust_difference_percent": -11.0,
                "min_effective_diameter_m": 0.22,
                "max_effective_diameter_m": 0.25,
            },
            {
                "variant_id": "WEAK",
                "root_ratio": 50,
                "tip_ratio": 50,
                "folded_diameter_ratio": 0.99,
                "compactness_gain_percent": 1.0,
                "thrust_diff_at_02": -50.0,
                "thrust_diff_at_04": -45.0,
                "thrust_diff_at_10": -30.0,
                "mean_thrust_difference_percent": -40.0,
                "min_effective_diameter_m": 0.24,
                "max_effective_diameter_m": 0.245,
            },
        ]
    )
    weak = next(row for row in rows if row.variant_id == "WEAK")
    assert weak.recommendation_note == RECOMMENDATION_NOT
