"""Tests for foldable V2 engineering design report generation."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.engineering_design_report import (
    KEY_RESULTS_NAME,
    MAIN_REPORT_NAME,
    REPORT_KEY_RESULTS_COLUMNS,
    build_report_key_results,
    generate_foldable_v2_engineering_design_report,
    load_engineering_report_metrics,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTERPOLATED_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "foldable"
    / "dynamics"
    / "physics"
    / "motor_coupled_7100rpm_interpolated_v2.csv"
)


@pytest.fixture(scope="module")
def report_metrics():
    if not INTERPOLATED_CSV.is_file():
        pytest.skip("Motor-coupled interpolated CSV not available")
    return load_engineering_report_metrics(INTERPOLATED_CSV)


def test_load_metrics_from_interpolated_csv(report_metrics) -> None:
    assert report_metrics.root_only_20cm_thrust_7100 == pytest.approx(3.73, abs=0.05)
    assert report_metrics.foldable_pretest_thrust_7100 == pytest.approx(6.37, abs=0.05)
    assert report_metrics.fixed_25cm_reference_thrust_7100 == pytest.approx(9.10, abs=0.05)
    assert report_metrics.gain_vs_compact_20cm_root_percent == pytest.approx(70.9, abs=1.0)
    assert report_metrics.loss_vs_25cm_reference_percent == pytest.approx(30.0, abs=2.0)
    assert report_metrics.motor_coupling_level == "reference_load_postprocess"


def test_key_results_has_required_metrics(report_metrics) -> None:
    rows = build_report_key_results(report_metrics)
    metrics = {row.metric for row in rows}
    required = {
        "root_only_20cm_thrust_7100",
        "foldable_pretest_thrust_7100",
        "fixed_25cm_reference_thrust_7100",
        "gain_vs_compact_20cm_root",
        "loss_vs_25cm_reference",
        "interpolated_throttle_7100",
        "motor_current_7100",
        "motor_power_7100",
        "aero_torque_root_20cm",
        "aero_torque_foldable",
        "motor_torque_margin_foldable",
        "motor_coupling_level",
    }
    assert required.issubset(metrics)


def test_generate_report_package(tmp_path: Path) -> None:
    if not INTERPOLATED_CSV.is_file():
        pytest.skip("Motor-coupled interpolated CSV not available")

    report_dir = tmp_path / "foldable_v2_engineering_design"
    written = generate_foldable_v2_engineering_design_report(
        PROJECT_ROOT,
        report_dir=report_dir,
    )
    assert len(written) == 5
    main_report = report_dir / MAIN_REPORT_NAME
    assert main_report.is_file()
    text = main_report.read_text(encoding="utf-8")
    for heading in (
        "## 1. Title and Abstract",
        "## 5. Modeling Architecture",
        "## 11. Motor-Coupled 7100 rpm Checkpoint",
        "## 15. Conclusion",
    ):
        assert heading in text

    key_csv = report_dir / KEY_RESULTS_NAME
    with key_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(REPORT_KEY_RESULTS_COLUMNS)
        assert len(list(reader)) == 12

    figure_index = (report_dir / "figure_index.md").read_text(encoding="utf-8")
    assert "constant_7100_thrust_split.png" in figure_index
    assert "Report-ready" in figure_index

    assumptions = (report_dir / "model_assumptions_and_limits.md").read_text(
        encoding="utf-8"
    )
    assert "reference_load_postprocess" in assumptions
    assert "No experimental validation" in assumptions

    conclusion_tr = (report_dir / "report_conclusion_tr.md").read_text(encoding="utf-8")
    assert "CFD/BEM" in conclusion_tr
    assert "20 cm" in conclusion_tr
