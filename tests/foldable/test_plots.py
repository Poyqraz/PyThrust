"""Foldable report plot tests."""

from pathlib import Path

import pytest

from pythrust.foldable.decision import (
    build_decision_matrix_from_csv,
    write_design_variant_decision_csv,
)
from pythrust.foldable.design_sweep import sweep_design_variants
from pythrust.foldable.models import load_config
from pythrust.foldable.plots import (
    FOLDABLE_REPORT_FIGURE_NAMES,
    FOLDABLE_REPORT_MARKDOWN_NAME,
    enrich_sweep_rows_for_plots,
    generate_foldable_report_figures,
    read_sweep_csv_for_plots,
)
from pythrust.foldable.summary import (
    summarize_design_variants_from_csv,
    write_design_variant_summary_csv,
)
from pythrust.foldable.validation import write_design_variant_sweep_csv
from pythrust.foldable.variants import DEFAULT_ROOT_TIP_RATIOS
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


def test_enrich_sweep_adds_throttle_zero_startup_point() -> None:
    rows = enrich_sweep_rows_for_plots(
        [
            {
                "variant_id": "V1",
                "throttle": 0.2,
                "rpm": 1000.0,
                "theta_deg": -10.0,
                "effective_diameter_m": 0.24,
                "foldable_thrust_n": 1.0,
                "fixed_thrust_n": 2.0,
                "thrust_difference_percent": -50.0,
                "compactness_ratio": 0.9,
            }
        ]
    )
    startup = next(row for row in rows if row["throttle"] == 0.0)
    assert startup["rpm"] == 0.0
    assert startup["theta_deg"] == -45.0
    assert startup["effective_diameter_m"] == pytest.approx(0.225)
    assert startup["foldable_thrust_n"] == 0.0


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
    assert len(written) == len(FOLDABLE_REPORT_FIGURE_NAMES) + 1
    for filename in FOLDABLE_REPORT_FIGURE_NAMES:
        figure_path = figures_dir / filename
        assert figure_path.is_file()
        assert figure_path.stat().st_size > 0
    report_path = figures_dir / FOLDABLE_REPORT_MARKDOWN_NAME
    assert report_path.is_file()
    content = report_path.read_text(encoding="utf-8")
    assert "reference_scaled" in content
    assert "moment-based" in content
    assert "active_window_diameter_growth_score" in content
    assert "fig_thrust_difference_normalized_250mm.png" in content


def test_normalized_thrust_field_present_after_enrichment(foldable_csv_bundle) -> None:
    sweep_path, _, _, _ = foldable_csv_bundle
    rows = enrich_sweep_rows_for_plots(read_sweep_csv_for_plots(sweep_path))
    assert all("thrust_difference_normalized_250mm" in row for row in rows)
    assert len({row["variant_id"] for row in rows}) == len(DEFAULT_ROOT_TIP_RATIOS)
