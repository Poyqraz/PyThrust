"""CSV çıktı kolonları ve tablo doğrulama yardımcıları."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence

from .comparison import (
    COMPARISON_COLUMNS,
    FixedVsFoldableComparisonRow,
)
from .design_sweep import DESIGN_VARIANT_SWEEP_COLUMNS, DesignVariantSweepRow
from .integration import FoldableOperatingPointResult
from .models import FoldableSweepRow

# Minimum V1 sweep kolonları (örnek script ve testler)
SWEEP_COLUMNS: tuple[str, ...] = (
    "rpm",
    "theta_deg",
    "effective_diameter_m",
    "thrust_n",
    "model_note",
)

# İleride PyThrust entegrasyonu için genişletilmiş kolonlar
EXTENDED_SWEEP_COLUMNS: tuple[str, ...] = SWEEP_COLUMNS + (
    "voltage_v",
    "throttle",
    "torque_nm",
    "current_a",
    "power_w",
    "efficiency",
)

OPERATING_POINT_COLUMNS: tuple[str, ...] = (
    "voltage_v",
    "throttle",
    "rpm",
    "theta_deg",
    "effective_diameter_m",
    "thrust_n",
    "torque_nm",
    "current_a",
    "power_w",
    "efficiency",
    "model_note",
)


def row_to_dict(row: FoldableSweepRow, columns: Sequence[str] = SWEEP_COLUMNS) -> dict[str, object]:
    """FoldableSweepRow'u sözlük olarak dönüştür."""
    full = {
        "rpm": row.rpm,
        "theta_deg": row.theta_deg,
        "effective_diameter_m": row.effective_diameter_m,
        "thrust_n": row.thrust_n,
        "model_note": row.model_note,
        "voltage_v": row.voltage_v,
        "throttle": row.throttle,
        "torque_nm": row.torque_nm,
        "current_a": row.current_a,
        "power_w": row.power_w,
        "efficiency": row.efficiency,
    }
    return {key: full[key] for key in columns}


def validate_sweep_columns(columns: Sequence[str]) -> list[str]:
    """Beklenen minimum kolonların varlığını doğrula; eksikleri döndür."""
    missing = [col for col in SWEEP_COLUMNS if col not in columns]
    return missing


def validate_sweep_rows(rows: Iterable[FoldableSweepRow]) -> list[str]:
    """Satırların minimum alanlarını doğrula; sorun listesi döndür."""
    issues: list[str] = []
    for index, row in enumerate(rows):
        if row.rpm < 0.0:
            issues.append(f"row[{index}]: rpm must be >= 0")
        if row.effective_diameter_m < 0.0:
            issues.append(f"row[{index}]: effective_diameter_m must be >= 0")
        if not row.model_note:
            issues.append(f"row[{index}]: model_note must not be empty")
    return issues


def write_sweep_csv(
    path: str | Path,
    rows: Sequence[FoldableSweepRow],
    *,
    columns: Sequence[str] = SWEEP_COLUMNS,
) -> Path:
    """Sweep satırlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_sweep_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(row_to_dict(row, columns))

    return output_path


def operating_point_to_dict(
    result: FoldableOperatingPointResult,
    columns: Sequence[str] = OPERATING_POINT_COLUMNS,
) -> dict[str, object]:
    """FoldableOperatingPointResult'u sözlük olarak dönüştür."""
    full = result.to_dict()
    return {key: full[key] for key in columns}


def validate_operating_point_columns(columns: Sequence[str]) -> list[str]:
    """Operating point CSV kolonlarını doğrula."""
    return [col for col in OPERATING_POINT_COLUMNS if col not in columns]


def write_operating_point_csv(
    path: str | Path,
    rows: Sequence[FoldableOperatingPointResult],
    *,
    columns: Sequence[str] = OPERATING_POINT_COLUMNS,
) -> Path:
    """Operating point sonuçlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_operating_point_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(operating_point_to_dict(row, columns))

    return output_path


def comparison_to_dict(
    row: FixedVsFoldableComparisonRow,
    columns: Sequence[str] = COMPARISON_COLUMNS,
) -> dict[str, object]:
    """FixedVsFoldableComparisonRow'u sözlük olarak dönüştür."""
    full = row.to_dict()
    return {key: full[key] for key in columns}


def validate_comparison_columns(columns: Sequence[str]) -> list[str]:
    """Karşılaştırma CSV kolonlarını doğrula."""
    return [col for col in COMPARISON_COLUMNS if col not in columns]


def write_comparison_csv(
    path: str | Path,
    rows: Sequence[FixedVsFoldableComparisonRow],
    *,
    columns: Sequence[str] = COMPARISON_COLUMNS,
) -> Path:
    """Sabit vs katlanabilir karşılaştırma sonuçlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_comparison_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(comparison_to_dict(row, columns))

    return output_path


def design_variant_to_dict(
    row: DesignVariantSweepRow,
    columns: Sequence[str] = DESIGN_VARIANT_SWEEP_COLUMNS,
) -> dict[str, object]:
    full = row.to_dict()
    return {key: full[key] for key in columns}


def validate_design_variant_columns(columns: Sequence[str]) -> list[str]:
    return [col for col in DESIGN_VARIANT_SWEEP_COLUMNS if col not in columns]


def write_design_variant_sweep_csv(
    path: str | Path,
    rows: Sequence[DesignVariantSweepRow],
    *,
    columns: Sequence[str] = DESIGN_VARIANT_SWEEP_COLUMNS,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_design_variant_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(design_variant_to_dict(row, columns))

    return output_path
