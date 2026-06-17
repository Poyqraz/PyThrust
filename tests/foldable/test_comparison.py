"""Fixed vs foldable comparison tests."""

import math
from pathlib import Path

import pytest

from pythrust.propellers.database import PropellerDatabase
from pythrust.foldable.comparison import (
    COMPARISON_COLUMNS,
    compute_thrust_difference_percent,
    evaluate_fixed_vs_foldable_comparison,
)
from pythrust.foldable.models import load_config
from pythrust.foldable.validation import validate_comparison_columns, write_comparison_csv


@pytest.fixture
def project_config():
    return load_config("configs/foldable/TIP_HINGED_250_V01.json")


@pytest.fixture
def prop_entry():
    db = PropellerDatabase()
    db.load(Path("data/propellers/apc_202602"), strict=False)
    entry = db.get("APC_10x4.7SF")
    assert entry is not None
    return entry


def test_comparison_columns_complete() -> None:
    assert validate_comparison_columns(COMPARISON_COLUMNS) == []


def test_thrust_difference_percent() -> None:
    assert math.isclose(compute_thrust_difference_percent(10.0, 12.0), 20.0)
    assert math.isclose(compute_thrust_difference_percent(10.0, 8.0), -20.0)
    assert compute_thrust_difference_percent(0.0, 5.0) == 0.0


def test_foldable_diameter_not_exceeding_open(project_config, prop_entry) -> None:
    row = evaluate_fixed_vs_foldable_comparison(project_config, prop_entry, throttle=0.8)
    assert row.foldable_effective_diameter_m <= project_config.geometry.diameter_open_m + 1e-9


def test_comparison_row_thrust_difference(project_config, prop_entry) -> None:
    row = evaluate_fixed_vs_foldable_comparison(project_config, prop_entry, throttle=0.6)
    expected = compute_thrust_difference_percent(row.fixed_thrust_n, row.foldable_thrust_n)
    assert math.isclose(row.thrust_difference_percent, expected, rel_tol=1e-9)


def test_comparison_csv_columns(tmp_path, project_config, prop_entry) -> None:
    row = evaluate_fixed_vs_foldable_comparison(project_config, prop_entry, throttle=0.5)
    output = tmp_path / "comparison.csv"
    write_comparison_csv(output, [row])
    content = output.read_text(encoding="utf-8")
    for col in COMPARISON_COLUMNS:
        assert col in content
