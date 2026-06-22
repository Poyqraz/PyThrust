"""Design variant summary tests."""

import math
from pathlib import Path

import pytest

from pythrust.foldable.design_sweep import sweep_design_variants
from pythrust.foldable.models import load_config
from pythrust.foldable.summary import (
    DESIGN_VARIANT_SUMMARY_COLUMNS,
    compactness_gain_percent,
    score_simple,
    summarize_design_variants,
    summarize_design_variants_from_csv,
    validate_design_variant_summary_columns,
    write_design_variant_summary_csv,
)
from pythrust.foldable.validation import write_design_variant_sweep_csv
from pythrust.foldable.variants import DEFAULT_ROOT_TIP_RATIOS
from pythrust.propellers.database import PropellerDatabase


@pytest.fixture
def sweep_csv(tmp_path):
    config = load_config("configs/foldable/TIP_HINGED_250_V01.json")
    db = PropellerDatabase()
    db.load(Path("data/propellers/apc_202602"), strict=False)
    prop_entry = db.get("APC_10x4.7SF")
    assert prop_entry is not None

    rows = sweep_design_variants(
        config,
        prop_entry,
        throttle_values=[0.2, 0.4, 0.6, 0.8, 1.0],
    )
    path = tmp_path / "design_variant_sweep.csv"
    write_design_variant_sweep_csv(path, rows)
    return path


def test_summary_columns_complete() -> None:
    assert validate_design_variant_summary_columns(DESIGN_VARIANT_SUMMARY_COLUMNS) == []


def test_summary_has_five_variants(sweep_csv) -> None:
    rows = summarize_design_variants_from_csv(sweep_csv)
    assert len(rows) == len(DEFAULT_ROOT_TIP_RATIOS)


def test_score_simple_calculation(sweep_csv) -> None:
    rows = summarize_design_variants_from_csv(sweep_csv)
    for row in rows:
        expected_gain = compactness_gain_percent(row.folded_diameter_ratio)
        assert math.isclose(row.compactness_gain_percent, expected_gain, rel_tol=1e-9)
        expected_score = score_simple(
            row.compactness_gain_percent,
            row.mean_thrust_difference_percent,
        )
        assert math.isclose(row.score_simple, expected_score, rel_tol=1e-9)


def test_folded_diameter_ratio_smaller_is_more_compact(sweep_csv) -> None:
    rows = {row.variant_id: row for row in summarize_design_variants_from_csv(sweep_csv)}
    compact = rows["TIP_HINGED_250_RT65_35"]
    less_compact = rows["TIP_HINGED_250_RT85_15"]
    assert compact.folded_diameter_ratio < less_compact.folded_diameter_ratio
    assert compact.compactness_gain_percent > less_compact.compactness_gain_percent


def test_summary_csv_columns(sweep_csv, tmp_path) -> None:
    rows = summarize_design_variants_from_csv(sweep_csv)
    output = tmp_path / "design_variant_summary.csv"
    write_design_variant_summary_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in DESIGN_VARIANT_SUMMARY_COLUMNS:
        assert col in content


def test_summarize_from_row_dicts(sweep_csv) -> None:
    from pythrust.foldable.summary import read_design_variant_sweep_csv

    sweep_rows = read_design_variant_sweep_csv(sweep_csv)
    summary_rows = summarize_design_variants(sweep_rows)
    assert len(summary_rows) == len(DEFAULT_ROOT_TIP_RATIOS)
    assert summary_rows[0].min_effective_diameter_m <= summary_rows[0].max_effective_diameter_m
