"""Moment tabanlı mafsal kinematiği doğrulama tabloları ve CSV çıktıları.

``moment_margin_nm = M_open - M_resist``:

- ``opening``: denge, margin yaklaşık 0
- ``saturated_open``: pozitif margin, fazla açılma momenti mekanik durakta
- ``folded``: ``M_open <= M_resist``, margin yaklaşık 0

V1 açılma momenti: ``M_open = m_tip * omega² * r_cg * lever_arm``;
``hinge_radius_m`` kullanılmaz (bkz. ``OPENING_MOMENT_V1_MODEL_NOTE``).
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from pythrust.propellers.database import PropellerEntry

from .design_sweep import DEFAULT_ROOT_TIP_RATIOS
from .effective_diameter import effective_diameter_m
from .integration import solve_pythrust_operating_point
from .kinematics import (
    MOMENT_MARGIN_NOTES,
    OPENING_MOMENT_V1_MODEL_NOTE,
    classify_hinge_state,
    opening_moment_nm,
    resisting_moment_nm,
    theta_deg_from_rpm,
)
from .models import FoldablePropellerConfig
from .variants import make_variant_config

MOMENT_KINEMATICS_VALIDATION_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "throttle",
    "rpm",
    "theta_deg",
    "effective_diameter_m",
    "opening_moment_nm",
    "resisting_moment_nm",
    "moment_margin_nm",
    "hinge_state",
)

VARIANT_PHYSICAL_PARAMETERS_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "tip_length_m",
    "tip_mass_kg",
    "tip_segment_cg_from_hinge_m",
    "hinge_radius_m",
    "hinge_stiffness_nm_per_rad",
    "hinge_friction_nm",
)


@dataclass(frozen=True)
class MomentKinematicsValidationRow:
    """Tek varyant + throttle için moment doğrulama satırı."""

    variant_id: str
    throttle: float
    rpm: float
    theta_deg: float
    effective_diameter_m: float
    opening_moment_nm: float
    resisting_moment_nm: float
    moment_margin_nm: float
    hinge_state: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VariantPhysicalParametersRow:
    """Varyant fiziksel parametre özeti."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    tip_length_m: float
    tip_mass_kg: float
    tip_segment_cg_from_hinge_m: float
    hinge_radius_m: float
    hinge_stiffness_nm_per_rad: float
    hinge_friction_nm: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_moment_validation_row(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
) -> MomentKinematicsValidationRow:
    """Sweep ile aynı RPM kaynağından moment doğrulama satırı üret."""
    operating_point = solve_pythrust_operating_point(config, prop_entry, throttle)
    rpm = operating_point.rpm
    theta_deg = theta_deg_from_rpm(rpm, config)
    d_eff = effective_diameter_m(theta_deg, config)
    m_open = opening_moment_nm(rpm, config.geometry, config.hinge)
    m_resist = resisting_moment_nm(theta_deg, config.hinge)
    margin = m_open - m_resist
    state = classify_hinge_state(
        rpm,
        theta_deg,
        m_open,
        m_resist,
        config.hinge,
    )
    return MomentKinematicsValidationRow(
        variant_id=config.id,
        throttle=throttle,
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=d_eff,
        opening_moment_nm=m_open,
        resisting_moment_nm=m_resist,
        moment_margin_nm=margin,
        hinge_state=state,
    )


def build_moment_kinematics_validation(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle_values: Sequence[float],
    *,
    ratios: Sequence[tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
) -> List[MomentKinematicsValidationRow]:
    """Tüm varyantlar ve throttle noktaları için doğrulama tablosu."""
    rows: List[MomentKinematicsValidationRow] = []
    for root_ratio, tip_ratio in ratios:
        variant_config = make_variant_config(base_config, root_ratio, tip_ratio)
        for throttle in throttle_values:
            rows.append(
                evaluate_moment_validation_row(variant_config, prop_entry, throttle)
            )
    return rows


def build_variant_physical_parameters(
    base_config: FoldablePropellerConfig,
    *,
    ratios: Sequence[tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
) -> List[VariantPhysicalParametersRow]:
    """Varyant fiziksel parametre tablosu."""
    rows: List[VariantPhysicalParametersRow] = []
    for root_ratio, tip_ratio in ratios:
        config = make_variant_config(base_config, root_ratio, tip_ratio)
        rows.append(
            VariantPhysicalParametersRow(
                variant_id=config.id,
                root_ratio=root_ratio,
                tip_ratio=tip_ratio,
                tip_length_m=config.geometry.tip_segment_length_m,
                tip_mass_kg=config.geometry.tip_segment_mass_kg,
                tip_segment_cg_from_hinge_m=config.geometry.tip_segment_cg_from_hinge_m,
                hinge_radius_m=config.hinge.hinge_radius_m,
                hinge_stiffness_nm_per_rad=config.hinge.hinge_stiffness_nm_per_rad,
                hinge_friction_nm=config.hinge.hinge_friction_nm,
            )
        )
    return rows


def _write_csv(
    path: str | Path,
    columns: Sequence[str],
    rows: Sequence[Dict[str, Any]],
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row[col] for col in columns})
    return output_path


def write_moment_kinematics_validation_csv(
    path: str | Path,
    rows: Sequence[MomentKinematicsValidationRow],
) -> Path:
    """Moment kinematics doğrulama CSV yaz."""
    return _write_csv(
        path,
        MOMENT_KINEMATICS_VALIDATION_COLUMNS,
        [row.to_dict() for row in rows],
    )


def write_variant_physical_parameters_csv(
    path: str | Path,
    rows: Sequence[VariantPhysicalParametersRow],
) -> Path:
    """Varyant fiziksel parametre CSV yaz."""
    return _write_csv(
        path,
        VARIANT_PHYSICAL_PARAMETERS_COLUMNS,
        [row.to_dict() for row in rows],
    )


def format_validation_table(
    rows: Sequence[MomentKinematicsValidationRow],
    *,
    limit: int | None = None,
) -> str:
    """Konsol için hizalı doğrulama tablosu."""
    selected = list(rows if limit is None else rows[:limit])
    header = (
        f"{'variant_id':>22} {'thr':>5} {'rpm':>6} {'theta':>7} "
        f"{'D_eff':>7} {'M_open':>8} {'M_res':>8} {'margin':>8} {'state':>15}"
    )
    lines = [header]
    for row in selected:
        lines.append(
            f"{row.variant_id:>22} {row.throttle:5.2f} {row.rpm:6.0f} "
            f"{row.theta_deg:7.2f} {row.effective_diameter_m:7.4f} "
            f"{row.opening_moment_nm:8.5f} {row.resisting_moment_nm:8.5f} "
            f"{row.moment_margin_nm:8.5f} {row.hinge_state:>15}"
        )
    lines.append("")
    lines.append(f"Model note: {OPENING_MOMENT_V1_MODEL_NOTE}")
    for state, note in MOMENT_MARGIN_NOTES.items():
        lines.append(f"  {state}: {note}")
    return "\n".join(lines)
