"""Compare thrust split modes at selected deployment states."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .physics_simulation import run_prescribed_rpm_physics
from .prescribed_rpm import PrescribedRpmConfig
from .split_thrust import (
    MODE_NOTES,
    THRUST_SPLIT_MODES,
    ThrustSplitMode,
    compute_split_thrust,
)
from .tip_aero_effectiveness import update_tip_aero_effectiveness

THRUST_SPLIT_COMPARISON_COLUMNS: tuple[str, ...] = (
    "case_id",
    "split_mode",
    "theta_final_deg",
    "D_root_m",
    "D_aero_m",
    "tip_radial_extension_m",
    "thrust_root_n",
    "thrust_tip_n",
    "thrust_total_n",
    "tip_fraction_of_total",
    "notes",
)


@dataclass(frozen=True)
class ThrustSplitComparisonRow:
    case_id: str
    split_mode: str
    theta_final_deg: float
    D_root_m: float
    D_aero_m: float
    tip_radial_extension_m: float
    thrust_root_n: float
    thrust_tip_n: float
    thrust_total_n: float
    tip_fraction_of_total: float
    notes: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "split_mode": self.split_mode,
            "theta_final_deg": self.theta_final_deg,
            "D_root_m": self.D_root_m,
            "D_aero_m": self.D_aero_m,
            "tip_radial_extension_m": self.tip_radial_extension_m,
            "thrust_root_n": self.thrust_root_n,
            "thrust_tip_n": self.thrust_tip_n,
            "thrust_total_n": self.thrust_total_n,
            "tip_fraction_of_total": self.tip_fraction_of_total,
            "notes": self.notes,
        }


def _final_tip_aero_effectiveness(
    config: FoldablePropellerConfig,
    thetas: Sequence[float],
    *,
    dt_s: float,
) -> float:
    eff = 0.0
    for theta in thetas:
        eff = update_tip_aero_effectiveness(eff, theta, dt_s=dt_s, config=config)
    return eff


def _run_case_final_state(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    case_id: str,
    deployment_bias_angle_deg: float = 0.0,
    stiffness_multiplier: float = 1.0,
    cent_moment_geometry_scale: float = 1.0,
    initial_stow_offset_deg: float = 0.0,
    open_latch_diagnostic: bool = False,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> tuple[float, float]:
    hinge = base_config.hinge
    cfg = replace(
        base_config,
        hinge=replace(
            hinge,
            cent_moment_model="geometric_radial",
            deployment_bias_angle_deg=deployment_bias_angle_deg,
            initial_stow_offset_deg=initial_stow_offset_deg,
            hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad * stiffness_multiplier,
            cent_moment_geometry_scale=cent_moment_geometry_scale,
            open_latch_diagnostic=open_latch_diagnostic,
        ),
    )
    sim = PrescribedRpmConfig(
        dt_s=dt_s,
        t_end_s=t_end_s,
        rpm_mode="constant",
        constant_rpm=constant_rpm,
    )
    states = run_prescribed_rpm_physics(cfg, prop_entry, sim=sim)
    thetas = [s.theta_deg for s in states]
    tip_eff = _final_tip_aero_effectiveness(cfg, thetas, dt_s=dt_s)
    return states[-1].theta_deg, tip_eff


def run_thrust_split_model_comparison(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    rho: float = 1.225,
) -> list[ThrustSplitComparisonRow]:
    """Compare split modes at selected deployment diagnostic cases."""
    case_specs: tuple[tuple[str, float, float, float, float, bool], ...] = (
        ("latch_theta0", 0.0, 1.0, 1.0, 175.0, True),
        ("bias5_k0.25_s3", 5.0, 0.25, 3.0, 0.0, False),
        ("bias5_k0.25_s5", 5.0, 0.25, 5.0, 0.0, False),
        ("bias10_k0.25_s5", 10.0, 0.25, 5.0, 0.0, False),
    )
    rows: list[ThrustSplitComparisonRow] = []

    for case_id, bias, k_mult, scale, offset, latch in case_specs:
        theta_final, tip_eff = _run_case_final_state(
            config,
            prop_entry,
            case_id=case_id,
            deployment_bias_angle_deg=bias,
            stiffness_multiplier=k_mult,
            cent_moment_geometry_scale=scale,
            initial_stow_offset_deg=offset,
            open_latch_diagnostic=latch,
            dt_s=dt_s,
            t_end_s=t_end_s,
            constant_rpm=constant_rpm,
        )
        for mode in THRUST_SPLIT_MODES:
            split = compute_split_thrust(
                rpm=constant_rpm,
                theta_deg=theta_final,
                tip_aero_effectiveness=tip_eff,
                config=config,
                prop_entry=prop_entry,
                rho=rho,
                split_mode=mode,
            )
            fraction = (
                split.thrust_tip_n / split.thrust_total_n
                if split.thrust_total_n > 0.0
                else 0.0
            )
            rows.append(
                ThrustSplitComparisonRow(
                    case_id=case_id,
                    split_mode=mode,
                    theta_final_deg=theta_final,
                    D_root_m=config.geometry.hinge_position_m * 2.0,
                    D_aero_m=split.aerodynamic_effective_diameter_m,
                    tip_radial_extension_m=split.tip_radial_extension_m,
                    thrust_root_n=split.thrust_root_n,
                    thrust_tip_n=split.thrust_tip_n,
                    thrust_total_n=split.thrust_total_n,
                    tip_fraction_of_total=fraction,
                    notes=MODE_NOTES[mode],
                )
            )
    return rows


def write_thrust_split_model_comparison_csv(
    path: str,
    rows: Sequence[ThrustSplitComparisonRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(THRUST_SPLIT_COMPARISON_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
