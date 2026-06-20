"""Extended tests for dynamic spin-up outputs (figures, frames, calibration)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pythrust.foldable.dynamics import (
    SPINUP_SUMMARY_CSV_COLUMNS,
    TUBITAK_LIFT_REFERENCE_FRACTION,
    TUBITAK_LIFT_TARGET_FRACTION,
    TUBITAK_PRETEST_RPM,
    export_spinup_frames,
    plot_spinup_summary,
    run_spinup_simulation,
    spinup_checkpoint_summary,
    tubitak_validation_summary,
    write_spinup_summary_csv,
)
from pythrust.foldable.models import load_config
from pythrust.foldable.variants import make_variant_config
from pythrust.propellers import PropellerDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
PROP_DB_PATH = PROJECT_ROOT / "data" / "propellers" / "apc_202602"


@pytest.fixture(scope="module")
def rt75_spinup_states():
    config = load_config(CONFIG_PATH)
    variant = make_variant_config(config, 75, 25)
    db = PropellerDatabase()
    db.load(PROP_DB_PATH, strict=False)
    prop_entry = db.get(variant.reference_propeller_id)
    if prop_entry is None:
        pytest.skip("Reference propeller not available in database")
    return variant, run_spinup_simulation(variant, prop_entry)


def test_plot_spinup_summary_writes_png(rt75_spinup_states, tmp_path: Path) -> None:
    variant, states = rt75_spinup_states
    output = plot_spinup_summary(
        states,
        tmp_path / "spinup_RT75_25.png",
        variant_label="RT75_25",
    )
    assert output.is_file()
    assert output.stat().st_size > 0


def test_export_spinup_frames_writes_pngs(rt75_spinup_states, tmp_path: Path) -> None:
    variant, states = rt75_spinup_states
    written = export_spinup_frames(
        states,
        variant,
        tmp_path,
        variant_label="RT75_25",
        frame_count=6,
    )
    assert len(written) == 6
    assert (tmp_path / "frames" / "RT75_25" / "frame_000.png").is_file()
    manifest = json.loads(
        (tmp_path / "frames" / "RT75_25" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["dynamic_rotation"] is True
    assert manifest["frame_count"] == 6


def test_tubitak_validation_summary(rt75_spinup_states) -> None:
    variant, states = rt75_spinup_states
    summary = tubitak_validation_summary(states, variant)
    assert summary.folded_start_theta_deg == pytest.approx(variant.hinge.theta_min_deg)
    assert summary.max_rpm > 0.0
    assert summary.max_thrust_n >= 0.0
    assert summary.open_diameter_m == pytest.approx(0.25)
    assert summary.pretest_rpm_target == pytest.approx(TUBITAK_PRETEST_RPM)


def test_load_config_optional_dynamics_fields() -> None:
    config = load_config(CONFIG_PATH)
    assert config.hinge.hinge_damping_nm_s_per_rad == pytest.approx(0.0)
    assert config.geometry.rotor_inertia_kgm2 is None


def test_spinup_checkpoint_summary_csv(rt75_spinup_states, tmp_path: Path) -> None:
    variant, states = rt75_spinup_states
    db = PropellerDatabase()
    db.load(PROP_DB_PATH, strict=False)
    prop_entry = db.get(variant.reference_propeller_id)
    assert prop_entry is not None
    summary = spinup_checkpoint_summary(states, variant, prop_entry)
    path = write_spinup_summary_csv(tmp_path / "dynamic_spinup_summary_RT75_25.csv", summary)
    import csv

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(SPINUP_SUMMARY_CSV_COLUMNS)
        rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    assert float(row["checkpoint_rpm"]) == pytest.approx(TUBITAK_PRETEST_RPM)
    assert float(row["current_pretest_ratio_target"]) == pytest.approx(
        TUBITAK_LIFT_REFERENCE_FRACTION
    )
    assert float(row["project_target_ratio"]) == pytest.approx(TUBITAK_LIFT_TARGET_FRACTION)
    assert summary.reference_thrust_at_7100_rpm > 0.0
    assert summary.thrust_ratio_at_7100_rpm is not None
