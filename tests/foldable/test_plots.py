"""Foldable report plot tests."""

from pathlib import Path

import pytest

from pythrust.foldable.design_sweep import sweep_design_variants
from pythrust.foldable.models import load_config
from pythrust.foldable.plots import (
    FOLDABLE_REPORT_FIGURE_NAMES,
    generate_foldable_report_figures,
)
from pythrust.foldable.summary import (
    summarize_design_variants_from_csv,
    write_design_variant_summary_csv,
)
from pythrust.foldable.decision import (
    build_decision_matrix_from_csv,
    write_design_variant_decision_csv,
)
from pythrust.foldable.validation import write_design_variant_sweep_csv
from pythrust.propellers.database import PropellerDatabase


@pytest.fixture
def foldable_csv_bundle(tmp_path):
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

    decision_rows = build_decision_matrix_from_csv(
        summary_path,
        sweep_csv_path=sweep_path,
    )
    decision_path = tmp_path / "design_variant_decision_matrix.csv"
    write_design_variant_decision_csv(decision_path, decision_rows)

    figures_dir = tmp_path / "figures"
    return sweep_path, summary_path, decision_path, figures_dir


def test_generate_foldable_report_figures_creates_expected_files(
    foldable_csv_bundle,
) -> None:
    sweep_path, summary_path, decision_path, figures_dir = foldable_csv_bundle
    written = generate_foldable_report_figures(
        sweep_csv_path=sweep_path,
        summary_csv_path=summary_path,
        decision_csv_path=decision_path,
        figures_dir=figures_dir,
    )
    assert len(written) == len(FOLDABLE_REPORT_FIGURE_NAMES)
    for filename in FOLDABLE_REPORT_FIGURE_NAMES:
        figure_path = figures_dir / filename
        assert figure_path.is_file()
        assert figure_path.stat().st_size > 0
