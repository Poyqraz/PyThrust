"""Validation ve CSV çıktı testleri."""

import csv
from pathlib import Path

import pytest

from pythrust.foldable.models import (
    CalibrationConfig,
    FoldableGeometry,
    FoldablePropellerConfig,
    FoldableSweepRow,
    HingeConfig,
    KinematicsConfig,
    MotorConfig,
    BatteryConfig,
    SystemConfig,
)
from pythrust.foldable.validation import (
    SWEEP_COLUMNS,
    validate_sweep_columns,
    validate_sweep_rows,
    write_sweep_csv,
)


@pytest.fixture
def sample_rows() -> list[FoldableSweepRow]:
    return [
        FoldableSweepRow(
            rpm=2000.0,
            theta_deg=-45.0,
            effective_diameter_m=0.2354,
            thrust_n=1.5,
            model_note="V1 test",
        ),
        FoldableSweepRow(
            rpm=8000.0,
            theta_deg=0.0,
            effective_diameter_m=0.25,
            thrust_n=12.0,
            model_note="V1 test",
        ),
    ]


def test_sweep_columns_complete() -> None:
    assert validate_sweep_columns(SWEEP_COLUMNS) == []


def test_sweep_columns_missing() -> None:
    missing = validate_sweep_columns(["rpm", "thrust_n"])
    assert "theta_deg" in missing
    assert "effective_diameter_m" in missing
    assert "model_note" in missing


def test_validate_rows_ok(sample_rows: list[FoldableSweepRow]) -> None:
    assert validate_sweep_rows(sample_rows) == []


def test_write_sweep_csv(tmp_path: Path, sample_rows: list[FoldableSweepRow]) -> None:
    output = tmp_path / "sweep.csv"
    write_sweep_csv(output, sample_rows)

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(SWEEP_COLUMNS)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["rpm"] == "2000.0"
        assert rows[1]["theta_deg"] == "0.0"
        assert rows[1]["effective_diameter_m"] == "0.25"
