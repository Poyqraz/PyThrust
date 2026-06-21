"""Tests for foldable V2 CFD preparation export layer."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pythrust.foldable.dynamics.cfd_preparation import (
    CFD_GEOMETRY_PARAMETERS_V2_COLUMNS,
    CFD_OPERATING_POINTS_V2_COLUMNS,
    CFD_READINESS_AUDIT_V2_COLUMNS,
    CFD_STATUS_NOTE,
    run_cfd_preparation_v2,
)
from pythrust.foldable.models import load_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
PROP_DB = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def v02_cfd_setup():
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROP_DB, strict=False)
    prop = db.get(config.reference_propeller_id)
    if prop is None:
        pytest.skip("Reference propeller not available")
    return config, prop


def test_cfd_preparation_generates_all_outputs(v02_cfd_setup, tmp_path: Path) -> None:
    config, prop = v02_cfd_setup
    paths = run_cfd_preparation_v2(
        config,
        prop,
        output_dir=tmp_path,
        t_end_s=0.3,
    )
    assert set(paths.keys()) == {
        "operating_points",
        "geometry",
        "recommendations",
        "audit",
        "boundary_notes",
    }
    for path in paths.values():
        assert path.is_file()
        assert path.stat().st_size > 0


def test_operating_points_required_cases(v02_cfd_setup, tmp_path: Path) -> None:
    config, prop = v02_cfd_setup
    paths = run_cfd_preparation_v2(config, prop, output_dir=tmp_path, t_end_s=0.3)
    with paths["operating_points"].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(CFD_OPERATING_POINTS_V2_COLUMNS)
        rows = list(reader)
    assert len(rows) == 5
    case_ids = {row["case_id"] for row in rows}
    assert "fixed_25cm_reference" in case_ids
    assert "root_only_20cm" in case_ids
    assert "latch_theta0" in case_ids
    for row in rows:
        assert float(row["rpm"]) == pytest.approx(7100.0, abs=1.0)
        assert "NOT CFD RESULT" in row["cfd_status_note"]


def test_geometry_parameters_not_missing(v02_cfd_setup, tmp_path: Path) -> None:
    config, prop = v02_cfd_setup
    paths = run_cfd_preparation_v2(config, prop, output_dir=tmp_path, t_end_s=0.3)
    with paths["geometry"].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(CFD_GEOMETRY_PARAMETERS_V2_COLUMNS)
        rows = list(reader)
    assert len(rows) == 5
    for row in rows:
        assert float(row["root_segment_length_m"]) > 0.0
        assert float(row["open_diameter_m"]) > 0.0
        assert row["expected_open_state"]
        assert CFD_STATUS_NOTE in row["cfd_status_note"]


def test_readiness_audit_and_recommendations(v02_cfd_setup, tmp_path: Path) -> None:
    config, prop = v02_cfd_setup
    paths = run_cfd_preparation_v2(config, prop, output_dir=tmp_path, t_end_s=0.3)
    with paths["recommendations"].open(newline="", encoding="utf-8") as handle:
        rec_rows = list(csv.DictReader(handle))
    priorities = [int(row["priority"]) for row in rec_rows]
    assert priorities == [1, 2, 3, 4, 5]
    assert rec_rows[0]["case_id"] == "fixed_25cm_reference"

    with paths["audit"].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(CFD_READINESS_AUDIT_V2_COLUMNS)
        audit_rows = list(reader)
    check_ids = {row["check_id"] for row in audit_rows}
    assert "cad_stl_availability" in check_ids
    assert "mesh_status" in check_ids
    rpm_check = next(row for row in audit_rows if row["check_id"] == "operating_rpm_exists")
    assert rpm_check["status"] == "pass"

    boundary = paths["boundary_notes"].read_text(encoding="utf-8")
    assert "NOT CFD RESULT" in boundary
    assert "MRF" in boundary
