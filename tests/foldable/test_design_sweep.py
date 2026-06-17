"""Design variant sweep tests."""

import math
from pathlib import Path

import pytest

from pythrust.foldable.design_sweep import (
    DESIGN_VARIANT_SWEEP_COLUMNS,
    sweep_design_variants,
)
from pythrust.foldable.models import load_config
from pythrust.foldable.variants import DEFAULT_ROOT_TIP_RATIOS, variant_id_from_ratios
from pythrust.foldable.validation import (
    validate_design_variant_columns,
    write_design_variant_sweep_csv,
)
from pythrust.propellers.database import PropellerDatabase


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


def test_design_variant_columns_complete() -> None:
    assert validate_design_variant_columns(DESIGN_VARIANT_SWEEP_COLUMNS) == []


def test_all_default_variants_present(project_config, prop_entry) -> None:
    rows = sweep_design_variants(
        project_config,
        prop_entry,
        throttle_values=[0.5],
    )
    variant_ids = {row.variant_id for row in rows}
    expected = {
        variant_id_from_ratios(root, tip)
        for root, tip in DEFAULT_ROOT_TIP_RATIOS
    }
    assert variant_ids == expected
    assert len(rows) == len(DEFAULT_ROOT_TIP_RATIOS)


def test_effective_diameter_not_exceeding_open(project_config, prop_entry) -> None:
    rows = sweep_design_variants(
        project_config,
        prop_entry,
        throttle_values=[0.2, 0.6, 1.0],
    )
    open_diameter_m = project_config.geometry.diameter_open_m
    for row in rows:
        assert row.effective_diameter_m <= open_diameter_m + 1e-9


def test_compactness_ratio_between_zero_and_one(project_config, prop_entry) -> None:
    rows = sweep_design_variants(
        project_config,
        prop_entry,
        throttle_values=[0.8],
    )
    for row in rows:
        assert 0.0 < row.compactness_ratio <= 1.0


def test_design_variant_csv_columns(tmp_path, project_config, prop_entry) -> None:
    rows = sweep_design_variants(
        project_config,
        prop_entry,
        throttle_values=[0.4],
    )
    output = tmp_path / "design_variant_sweep.csv"
    write_design_variant_sweep_csv(output, rows)
    content = output.read_text(encoding="utf-8")
    for col in DESIGN_VARIANT_SWEEP_COLUMNS:
        assert col in content


def test_thrust_difference_matches_formula(project_config, prop_entry) -> None:
    from pythrust.foldable.comparison import compute_thrust_difference_percent

    rows = sweep_design_variants(
        project_config,
        prop_entry,
        throttle_values=[0.6],
    )
    for row in rows:
        expected = compute_thrust_difference_percent(
            row.fixed_thrust_n,
            row.foldable_thrust_n,
        )
        assert math.isclose(row.thrust_difference_percent, expected, rel_tol=1e-9)
