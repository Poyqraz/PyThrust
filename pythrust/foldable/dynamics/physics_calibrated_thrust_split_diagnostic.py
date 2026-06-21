"""Calibrated effective-diameter delta thrust split diagnostic CSV."""

from __future__ import annotations

import csv
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import (
    aerodynamic_effective_diameter_m,
    geometric_effective_diameter_from_config,
    root_diameter_m,
)
from ..models import FoldablePropellerConfig
from .physics_thrust_split_diagnostic import _run_case_final_state
from .thrust_split_calibration import (
    CalibratedThrustSplitDiagnostics,
    compute_calibrated_thrust_split_diagnostics,
)

CALIBRATED_THRUST_SPLIT_DIAGNOSTIC_COLUMNS: tuple[str, ...] = (
    "case_id",
    "D_root_m",
    "D_aero_m",
    "D_open_m",
    "T_root_n",
    "T_tip_ideal_delta_n",
    "T_total_ideal_n",
    "reference_total_25cm_n",
    "pretest_ratio",
    "pretest_required_total_n",
    "pretest_required_tip_n",
    "pretest_tip_efficiency_factor",
    "target_ratio",
    "target_required_total_n",
    "target_required_tip_n",
    "target_tip_efficiency_factor",
    "selected_tip_efficiency_factor",
    "T_tip_calibrated_n",
    "T_total_calibrated_n",
)


def run_calibrated_thrust_split_diagnostic(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
    rho: float = 1.225,
) -> list[CalibratedThrustSplitDiagnostics]:
    """Calibration breakdown at selected deployment cases."""
    case_specs: tuple[tuple[str, float, float, float, float, bool], ...] = (
        ("latch_theta0", 0.0, 1.0, 1.0, 175.0, True),
        ("bias5_k0.25_s3", 5.0, 0.25, 3.0, 0.0, False),
        ("bias5_k0.25_s5", 5.0, 0.25, 5.0, 0.0, False),
        ("bias10_k0.25_s5", 10.0, 0.25, 5.0, 0.0, False),
    )
    d_open = config.geometry.diameter_open_m
    d_root = root_diameter_m(config.geometry)
    rows: list[CalibratedThrustSplitDiagnostics] = []

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
        d_geo = geometric_effective_diameter_from_config(theta_final, config)
        d_aero = aerodynamic_effective_diameter_m(
            d_geo,
            root_diameter_m=d_root,
            tip_aero_effectiveness=tip_eff,
        )
        rows.append(
            compute_calibrated_thrust_split_diagnostics(
                case_id=case_id,
                rpm=constant_rpm,
                d_root=d_root,
                d_aero=d_aero,
                d_open=d_open,
                config=config,
                prop_entry=prop_entry,
                rho=rho,
            )
        )
    return rows


def write_calibrated_thrust_split_diagnostic_csv(
    path: str,
    rows: Sequence[CalibratedThrustSplitDiagnostics],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(CALIBRATED_THRUST_SPLIT_DIAGNOSTIC_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
