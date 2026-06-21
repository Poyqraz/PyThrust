"""Tests for foldable design decision matrix and candidate ranking."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.physics_foldable_design_decision import (
    FOLDABLE_CANDIDATE_RANKING_V2_COLUMNS,
    FOLDABLE_DESIGN_DECISION_MATRIX_V2_COLUMNS,
    run_foldable_candidate_ranking_v2,
    run_foldable_design_decision_matrix_v2,
    write_foldable_candidate_ranking_v2_csv,
    write_foldable_design_decision_matrix_v2_csv,
)
from pythrust.foldable.models import load_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
PROP_DB = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def v02_physics_setup():
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROP_DB, strict=False)
    prop = db.get(config.reference_propeller_id)
    if prop is None:
        pytest.skip("Reference propeller not available")
    return config, prop


def test_design_decision_matrix_csv(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    rows = run_foldable_design_decision_matrix_v2(
        config,
        prop,
        variant_ratios=(None, (75, 25)),
        t_end_s=0.3,
    )
    assert len(rows) == 12
    labels = {row.decision_label for row in rows if row.decision_label}
    assert "compact_root_baseline" in labels
    assert "current_pretest_candidate" in labels
    assert "partial_deployment_candidate" in labels

    path = tmp_path / "foldable_design_decision_matrix_v2.csv"
    write_foldable_design_decision_matrix_v2_csv(str(path), rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(FOLDABLE_DESIGN_DECISION_MATRIX_V2_COLUMNS)


def test_candidate_ranking_orders_by_pretest(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    decision_rows = run_foldable_design_decision_matrix_v2(
        config, prop, variant_ratios=(None,), t_end_s=0.3
    )
    ranking_rows = run_foldable_candidate_ranking_v2(decision_rows)
    assert len(ranking_rows) == 4
    assert ranking_rows[0].rank_pretest == 1
    assert ranking_rows[0].case_id == "latch_theta0"
    no_latch = [r for r in ranking_rows if not r.needs_latch]
    assert no_latch[0].case_id == "bias5_k0.25_s5"


def test_partial_case_differs_from_latch(v02_physics_setup) -> None:
    config, prop = v02_physics_setup
    rows = run_foldable_design_decision_matrix_v2(
        config, prop, variant_ratios=(None,), t_end_s=2.0
    )
    latch = next(r for r in rows if r.case_id == "latch_theta0")
    partial = next(r for r in rows if r.case_id == "bias10_k0.25_s5")
    assert partial.T_total_pretest_fixed_n < latch.T_total_pretest_fixed_n
    assert partial.requires_latch_flag is False
    assert latch.requires_latch_flag is True
    assert latch.ratio_to_25cm_pretest > partial.ratio_to_25cm_pretest


def test_candidate_ranking_csv(v02_physics_setup, tmp_path: Path) -> None:
    config, prop = v02_physics_setup
    decision_rows = run_foldable_design_decision_matrix_v2(
        config, prop, variant_ratios=(None,), t_end_s=0.3
    )
    ranking_rows = run_foldable_candidate_ranking_v2(decision_rows)
    path = tmp_path / "foldable_candidate_ranking_v2.csv"
    write_foldable_candidate_ranking_v2_csv(str(path), ranking_rows)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(FOLDABLE_CANDIDATE_RANKING_V2_COLUMNS)
