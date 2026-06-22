"""Tip thrust activation pipeline diagnostics."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from .aero_effectiveness import deployment_progress_from_theta
from ..models import FoldablePropellerConfig
from .physics_simulation import run_prescribed_rpm_physics
from .prescribed_rpm import PrescribedRpmConfig
from .split_thrust import compute_tip_thrust_breakdown
from .tip_aero_effectiveness import geometric_tip_exposure_01, update_tip_aero_effectiveness

TIP_THRUST_ACTIVATION_COLUMNS: tuple[str, ...] = (
    "case_id",
    "bias_deg",
    "stiffness_multiplier",
    "moment_scale",
    "open_latch_diagnostic",
    "theta_final_deg",
    "deployment_progress_final",
    "tip_radial_extension_m",
    "geometric_effective_diameter_m",
    "aerodynamic_effective_diameter_m",
    "tip_aero_effectiveness_final",
    "exposed_tip_fraction_final",
    "d_tip_equiv_m",
    "thrust_tip_raw_n",
    "thrust_tip_after_effectiveness_n",
    "thrust_tip_final_n",
    "thrust_root_final_n",
    "hinge_state",
)


@dataclass(frozen=True)
class TipThrustActivationRow:
    case_id: str
    bias_deg: float
    stiffness_multiplier: float
    moment_scale: float
    open_latch_diagnostic: bool
    theta_final_deg: float
    deployment_progress_final: float
    tip_radial_extension_m: float
    geometric_effective_diameter_m: float
    aerodynamic_effective_diameter_m: float
    tip_aero_effectiveness_final: float
    exposed_tip_fraction_final: float
    d_tip_equiv_m: float
    thrust_tip_raw_n: float
    thrust_tip_after_effectiveness_n: float
    thrust_tip_final_n: float
    thrust_root_final_n: float
    hinge_state: str

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "case_id": self.case_id,
            "bias_deg": self.bias_deg,
            "stiffness_multiplier": self.stiffness_multiplier,
            "moment_scale": self.moment_scale,
            "open_latch_diagnostic": self.open_latch_diagnostic,
            "theta_final_deg": self.theta_final_deg,
            "deployment_progress_final": self.deployment_progress_final,
            "tip_radial_extension_m": self.tip_radial_extension_m,
            "geometric_effective_diameter_m": self.geometric_effective_diameter_m,
            "aerodynamic_effective_diameter_m": self.aerodynamic_effective_diameter_m,
            "tip_aero_effectiveness_final": self.tip_aero_effectiveness_final,
            "exposed_tip_fraction_final": self.exposed_tip_fraction_final,
            "d_tip_equiv_m": self.d_tip_equiv_m,
            "thrust_tip_raw_n": self.thrust_tip_raw_n,
            "thrust_tip_after_effectiveness_n": self.thrust_tip_after_effectiveness_n,
            "thrust_tip_final_n": self.thrust_tip_final_n,
            "thrust_root_final_n": self.thrust_root_final_n,
            "hinge_state": self.hinge_state,
        }


def _final_tip_aero_effectiveness(
    config: FoldablePropellerConfig,
    states_theta: Sequence[float],
    *,
    dt_s: float,
) -> float:
    eff = 0.0
    for theta in states_theta:
        eff = update_tip_aero_effectiveness(eff, theta, dt_s=dt_s, config=config)
    return eff


def _run_tip_activation_case(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    case_id: str,
    bias_deg: float,
    stiffness_multiplier: float,
    moment_scale: float,
    initial_stow_offset_deg: float = 0.0,
    open_latch_diagnostic: bool = False,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> TipThrustActivationRow:
    hinge = base_config.hinge
    new_hinge = replace(
        hinge,
        cent_moment_model="geometric_radial",
        deployment_bias_angle_deg=bias_deg,
        initial_stow_offset_deg=initial_stow_offset_deg,
        hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad * stiffness_multiplier,
        cent_moment_geometry_scale=moment_scale,
        open_latch_diagnostic=open_latch_diagnostic,
    )
    cfg = replace(base_config, hinge=new_hinge)
    sim = PrescribedRpmConfig(
        dt_s=dt_s,
        t_end_s=t_end_s,
        rpm_mode="constant",
        constant_rpm=constant_rpm,
    )
    states = run_prescribed_rpm_physics(cfg, prop_entry, sim=sim)
    final = states[-1]
    thetas = [s.theta_deg for s in states]
    lagged_eff = _final_tip_aero_effectiveness(cfg, thetas, dt_s=dt_s)
    geom_exposure = geometric_tip_exposure_01(final.theta_deg, cfg)
    breakdown = compute_tip_thrust_breakdown(
        rpm=constant_rpm,
        theta_deg=final.theta_deg,
        tip_aero_effectiveness=lagged_eff,
        config=cfg,
        prop_entry=prop_entry,
        rho=sim.rho_kg_m3,
    )
    progress = deployment_progress_from_theta(
        final.theta_deg,
        theta_min_deg=hinge.theta_min_deg,
        theta_max_deg=hinge.theta_max_deg,
    )
    return TipThrustActivationRow(
        case_id=case_id,
        bias_deg=bias_deg,
        stiffness_multiplier=stiffness_multiplier,
        moment_scale=moment_scale,
        open_latch_diagnostic=open_latch_diagnostic,
        theta_final_deg=final.theta_deg,
        deployment_progress_final=progress,
        tip_radial_extension_m=breakdown.tip_radial_extension_m,
        geometric_effective_diameter_m=breakdown.geometric_effective_diameter_m,
        aerodynamic_effective_diameter_m=breakdown.aerodynamic_effective_diameter_m,
        tip_aero_effectiveness_final=lagged_eff,
        exposed_tip_fraction_final=breakdown.exposed_tip_fraction,
        d_tip_equiv_m=breakdown.d_tip_equiv_m,
        thrust_tip_raw_n=breakdown.thrust_tip_raw_n,
        thrust_tip_after_effectiveness_n=breakdown.thrust_tip_after_effectiveness_n,
        thrust_tip_final_n=breakdown.thrust_tip_final_n,
        thrust_root_final_n=final.thrust_root_n,
        hinge_state=final.hinge_state,
    )


def run_tip_thrust_activation_diagnostic(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> list[TipThrustActivationRow]:
    """Selected bias × stiffness × scale cases with thrust pipeline breakdown."""
    bias_values = (10.0, 20.0, 30.0)
    stiffness_multipliers = (0.25, 0.5)
    moment_scales = (1.0, 3.0, 5.0)
    rows: list[TipThrustActivationRow] = []
    for bias in bias_values:
        for k_mult in stiffness_multipliers:
            for scale in moment_scales:
                case_id = f"tip_bias{bias:g}_k{k_mult:g}_s{scale:g}"
                rows.append(
                    _run_tip_activation_case(
                        config,
                        prop_entry,
                        case_id=case_id,
                        bias_deg=bias,
                        stiffness_multiplier=k_mult,
                        moment_scale=scale,
                        dt_s=dt_s,
                        t_end_s=t_end_s,
                        constant_rpm=constant_rpm,
                    )
                )
    return rows


def run_tip_thrust_latch_comparison(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> list[TipThrustActivationRow]:
    """Same cases with and without open latch; includes near-open start for latch demo."""
    specs = (
        (30.0, 0.25, 5.0, 0.0, False),
        (30.0, 0.25, 5.0, 0.0, True),
        (10.0, 0.25, 3.0, 175.0, True),
        (0.0, 1.0, 1.0, 175.0, True),
    )
    rows: list[TipThrustActivationRow] = []
    for bias, k_mult, scale, offset, latch in specs:
        suffix = "latch" if latch else "free"
        case_id = f"tip_{suffix}_bias{bias:g}_k{k_mult:g}_s{scale:g}_o{offset:g}"
        rows.append(
            _run_tip_activation_case(
                config,
                prop_entry,
                case_id=case_id,
                bias_deg=bias,
                stiffness_multiplier=k_mult,
                moment_scale=scale,
                open_latch_diagnostic=latch,
                initial_stow_offset_deg=offset,
                dt_s=dt_s,
                t_end_s=t_end_s,
                constant_rpm=constant_rpm,
            )
        )
    return rows


def write_tip_thrust_activation_csv(
    path: str,
    rows: Sequence[TipThrustActivationRow],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TIP_THRUST_ACTIVATION_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
