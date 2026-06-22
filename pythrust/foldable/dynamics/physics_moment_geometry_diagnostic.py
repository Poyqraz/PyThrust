"""Diagnostic comparison of hinge opening-moment geometry variants."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .physics_stability import analyze_physics_stability
from .physics_simulation import run_prescribed_rpm_physics
from .prescribed_rpm import PrescribedRpmConfig

MOMENT_GEOMETRY_DIAGNOSTIC_COLUMNS: tuple[str, ...] = (
    "model_variant",
    "deployment_bias_angle_deg",
    "hinge_stiffness",
    "theta_final_deg",
    "D_geo_final_m",
    "D_aero_final_m",
    "thrust_tip_final_n",
    "hinge_state",
    "stable_flag",
)


@dataclass(frozen=True)
class MomentGeometryDiagnosticRow:
    model_variant: str
    deployment_bias_angle_deg: float
    hinge_stiffness: float
    theta_final_deg: float
    D_geo_final_m: float
    D_aero_final_m: float
    thrust_tip_final_n: float
    hinge_state: str
    stable_flag: bool

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "model_variant": self.model_variant,
            "deployment_bias_angle_deg": self.deployment_bias_angle_deg,
            "hinge_stiffness": self.hinge_stiffness,
            "theta_final_deg": self.theta_final_deg,
            "D_geo_final_m": self.D_geo_final_m,
            "D_aero_final_m": self.D_aero_final_m,
            "thrust_tip_final_n": self.thrust_tip_final_n,
            "hinge_state": self.hinge_state,
            "stable_flag": self.stable_flag,
        }


def _run_variant(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    model_variant: str,
    cent_moment_model: str,
    deployment_bias_angle_deg: float = 0.0,
    initial_stow_offset_deg: float = 0.0,
    stiffness_multiplier: float = 1.0,
    cent_moment_geometry_scale: float = 1.0,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> MomentGeometryDiagnosticRow:
    hinge = base_config.hinge
    new_hinge = replace(
        hinge,
        cent_moment_model=cent_moment_model,
        deployment_bias_angle_deg=deployment_bias_angle_deg,
        initial_stow_offset_deg=initial_stow_offset_deg,
        hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad * stiffness_multiplier,
        cent_moment_geometry_scale=cent_moment_geometry_scale,
    )
    cfg = replace(base_config, hinge=new_hinge)
    sim = PrescribedRpmConfig(
        dt_s=dt_s,
        t_end_s=t_end_s,
        rpm_mode="constant",
        constant_rpm=constant_rpm,
    )
    states = run_prescribed_rpm_physics(cfg, prop_entry, sim=sim)
    metrics = analyze_physics_stability(
        states,
        cfg,
        case_id=model_variant,
        rpm_profile=f"constant_{constant_rpm:g}",
        dt_s=dt_s,
    )
    final = states[-1]
    return MomentGeometryDiagnosticRow(
        model_variant=model_variant,
        deployment_bias_angle_deg=deployment_bias_angle_deg,
        hinge_stiffness=new_hinge.hinge_stiffness_nm_per_rad,
        theta_final_deg=final.theta_deg,
        D_geo_final_m=final.geometric_effective_diameter_m,
        D_aero_final_m=final.aerodynamic_effective_diameter_m,
        thrust_tip_final_n=final.thrust_tip_n,
        hinge_state=final.hinge_state,
        stable_flag=metrics.stable_flag,
    )


def run_moment_geometry_diagnostic_cases(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> list[MomentGeometryDiagnosticRow]:
    """Run prescribed diagnostic variants comparing moment geometry models."""
    common = {"dt_s": dt_s, "t_end_s": t_end_s, "constant_rpm": constant_rpm}
    return [
        _run_variant(
            config,
            prop_entry,
            model_variant="progress_lever_baseline",
            cent_moment_model="progress_lever",
            **common,
        ),
        _run_variant(
            config,
            prop_entry,
            model_variant="geometric_radial_no_offset",
            cent_moment_model="geometric_radial",
            **common,
        ),
        _run_variant(
            config,
            prop_entry,
            model_variant="geometric_radial_bias_10deg",
            cent_moment_model="geometric_radial",
            deployment_bias_angle_deg=10.0,
            **common,
        ),
        _run_variant(
            config,
            prop_entry,
            model_variant="geometric_radial_reduced_stiffness",
            cent_moment_model="geometric_radial",
            stiffness_multiplier=0.25,
            **common,
        ),
        _run_variant(
            config,
            prop_entry,
            model_variant="geometric_radial_scale_2x",
            cent_moment_model="geometric_radial",
            cent_moment_geometry_scale=2.0,
            **common,
        ),
    ]


def write_moment_geometry_diagnostic_csv(
    path: str,
    rows: Sequence[MomentGeometryDiagnosticRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MOMENT_GEOMETRY_DIAGNOSTIC_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
