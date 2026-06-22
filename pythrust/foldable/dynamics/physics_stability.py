"""Stability and diagnostic analysis for prescribed-RPM V2 physics."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .hinge_moments import centrifugal_moment_nm, stiffness_moment_nm
from .physics_simulation import run_prescribed_rpm_physics
from .physics_state import PhysicsState
from .prescribed_rpm import PrescribedRpmConfig

STABILITY_REPORT_COLUMNS: tuple[str, ...] = (
    "case_id",
    "rpm_profile",
    "dt_s",
    "hinge_stiffness_nm_per_rad",
    "hinge_damping_nm_s_per_rad",
    "hinge_friction_nm",
    "hinge_inertia_kgm2",
    "aero_hinge_moment_gain",
    "theta_final_deg",
    "theta_dot_final_deg_s",
    "theta_dot_rms_last_20_percent",
    "theta_ddot_rms_last_20_percent",
    "M_net_rms_last_20_percent",
    "D_geo_final_m",
    "D_aero_final_m",
    "thrust_root_final_n",
    "thrust_tip_final_n",
    "thrust_total_final_n",
    "stable_flag",
    "chattering_flag",
    "numerical_sensitivity_flag",
    "notes",
)

DIAGNOSTIC_SWEEP_COLUMNS: tuple[str, ...] = (
    "case_id",
    "stiffness_multiplier",
    "damping_multiplier",
    "aero_gain_multiplier",
    "theta_final_deg",
    "D_aero_final_m",
    "thrust_tip_final_n",
    "chattering_flag",
    "stable_flag",
)


@dataclass(frozen=True)
class StabilityMetrics:
    case_id: str
    rpm_profile: str
    dt_s: float
    hinge_stiffness_nm_per_rad: float
    hinge_damping_nm_s_per_rad: float
    hinge_friction_nm: float
    hinge_inertia_kgm2: float
    aero_hinge_moment_gain: float
    theta_final_deg: float
    theta_dot_final_deg_s: float
    theta_dot_rms_last_20_percent: float
    theta_ddot_rms_last_20_percent: float
    M_net_rms_last_20_percent: float
    D_geo_final_m: float
    D_aero_final_m: float
    thrust_root_final_n: float
    thrust_tip_final_n: float
    thrust_total_final_n: float
    stable_flag: bool
    chattering_flag: bool
    numerical_sensitivity_flag: bool = False
    notes: str = ""

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "case_id": self.case_id,
            "rpm_profile": self.rpm_profile,
            "dt_s": self.dt_s,
            "hinge_stiffness_nm_per_rad": self.hinge_stiffness_nm_per_rad,
            "hinge_damping_nm_s_per_rad": self.hinge_damping_nm_s_per_rad,
            "hinge_friction_nm": self.hinge_friction_nm,
            "hinge_inertia_kgm2": self.hinge_inertia_kgm2,
            "aero_hinge_moment_gain": self.aero_hinge_moment_gain,
            "theta_final_deg": self.theta_final_deg,
            "theta_dot_final_deg_s": self.theta_dot_final_deg_s,
            "theta_dot_rms_last_20_percent": self.theta_dot_rms_last_20_percent,
            "theta_ddot_rms_last_20_percent": self.theta_ddot_rms_last_20_percent,
            "M_net_rms_last_20_percent": self.M_net_rms_last_20_percent,
            "D_geo_final_m": self.D_geo_final_m,
            "D_aero_final_m": self.D_aero_final_m,
            "thrust_root_final_n": self.thrust_root_final_n,
            "thrust_tip_final_n": self.thrust_tip_final_n,
            "thrust_total_final_n": self.thrust_total_final_n,
            "stable_flag": self.stable_flag,
            "chattering_flag": self.chattering_flag,
            "numerical_sensitivity_flag": self.numerical_sensitivity_flag,
            "notes": self.notes,
        }


def _rms(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


def _tail_fraction(states: Sequence[PhysicsState], fraction: float = 0.2) -> list[PhysicsState]:
    if not states:
        return []
    start = max(0, int(len(states) * (1.0 - fraction)))
    return list(states[start:])


def _detect_chattering(tail: Sequence[PhysicsState]) -> bool:
    if len(tail) < 10:
        return False
    dots = [s.theta_dot_deg_s for s in tail]
    sign_changes = sum(
        1
        for a, b in zip(dots, dots[1:])
        if a * b < 0.0 and abs(a) > 0.05 and abs(b) > 0.05
    )
    dot_rms = _rms(dots)
    return sign_changes >= 8 or dot_rms > 5.0


def _detect_stable(tail: Sequence[PhysicsState]) -> bool:
    if not tail:
        return False
    dot_rms = _rms([s.theta_dot_deg_s for s in tail])
    ddot_rms = _rms([s.theta_ddot_deg_s2 for s in tail])
    mnet_rms = _rms([s.M_net_nm for s in tail])
    return dot_rms < 2.0 and ddot_rms < 200.0 and mnet_rms < 0.05


def analyze_physics_stability(
    states: Sequence[PhysicsState],
    config: FoldablePropellerConfig,
    *,
    case_id: str,
    rpm_profile: str,
    dt_s: float,
    numerical_sensitivity_flag: bool = False,
    notes: str = "",
) -> StabilityMetrics:
    """Compute stability metrics from a physics simulation history."""
    tail = _tail_fraction(states, 0.2)
    final = states[-1] if states else None
    hinge = config.hinge
    inertia = hinge.hinge_inertia_kgm2 if hinge.hinge_inertia_kgm2 is not None else 0.0

    if final is None:
        return StabilityMetrics(
            case_id=case_id,
            rpm_profile=rpm_profile,
            dt_s=dt_s,
            hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad,
            hinge_damping_nm_s_per_rad=hinge.hinge_damping_nm_s_per_rad,
            hinge_friction_nm=hinge.hinge_friction_nm,
            hinge_inertia_kgm2=inertia,
            aero_hinge_moment_gain=hinge.aero_hinge_moment_gain,
            theta_final_deg=0.0,
            theta_dot_final_deg_s=0.0,
            theta_dot_rms_last_20_percent=0.0,
            theta_ddot_rms_last_20_percent=0.0,
            M_net_rms_last_20_percent=0.0,
            D_geo_final_m=0.0,
            D_aero_final_m=0.0,
            thrust_root_final_n=0.0,
            thrust_tip_final_n=0.0,
            thrust_total_final_n=0.0,
            stable_flag=False,
            chattering_flag=False,
            numerical_sensitivity_flag=numerical_sensitivity_flag,
            notes=notes or "empty history",
        )

    chattering = _detect_chattering(tail)
    stable = _detect_stable(tail) and not chattering

    return StabilityMetrics(
        case_id=case_id,
        rpm_profile=rpm_profile,
        dt_s=dt_s,
        hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad,
        hinge_damping_nm_s_per_rad=hinge.hinge_damping_nm_s_per_rad,
        hinge_friction_nm=hinge.hinge_friction_nm,
        hinge_inertia_kgm2=inertia,
        aero_hinge_moment_gain=hinge.aero_hinge_moment_gain,
        theta_final_deg=final.theta_deg,
        theta_dot_final_deg_s=final.theta_dot_deg_s,
        theta_dot_rms_last_20_percent=_rms([s.theta_dot_deg_s for s in tail]),
        theta_ddot_rms_last_20_percent=_rms([s.theta_ddot_deg_s2 for s in tail]),
        M_net_rms_last_20_percent=_rms([s.M_net_nm for s in tail]),
        D_geo_final_m=final.geometric_effective_diameter_m,
        D_aero_final_m=final.aerodynamic_effective_diameter_m,
        thrust_root_final_n=final.thrust_root_n,
        thrust_tip_final_n=final.thrust_tip_n,
        thrust_total_final_n=final.thrust_total_n,
        stable_flag=stable,
        chattering_flag=chattering,
        numerical_sensitivity_flag=numerical_sensitivity_flag,
        notes=notes,
    )


def write_stability_report(
    path: str,
    rows: Sequence[StabilityMetrics],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(STABILITY_REPORT_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_diagnostic_sweep_csv(
    path: str,
    rows: Sequence[dict[str, str | float | bool]],
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DIAGNOSTIC_SWEEP_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def scaled_hinge_config(
    config: FoldablePropellerConfig,
    *,
    stiffness_multiplier: float = 1.0,
    damping_multiplier: float = 1.0,
    aero_gain_multiplier: float = 1.0,
) -> FoldablePropellerConfig:
    """Return a copy with scaled hinge parameters for diagnostic sweeps."""
    hinge = config.hinge
    new_hinge = replace(
        hinge,
        hinge_stiffness_nm_per_rad=hinge.hinge_stiffness_nm_per_rad * stiffness_multiplier,
        hinge_damping_nm_s_per_rad=hinge.hinge_damping_nm_s_per_rad * damping_multiplier,
        aero_hinge_moment_gain=hinge.aero_hinge_moment_gain * aero_gain_multiplier,
    )
    return replace(config, hinge=new_hinge)


def run_dt_sensitivity_cases(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_values: Sequence[float] = (0.002, 0.001, 0.0005),
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> list[StabilityMetrics]:
    """Run constant-RPM cases at multiple dt for numerical sensitivity check."""
    results: list[StabilityMetrics] = []
    final_thetas: list[float] = []

    for dt_s in dt_values:
        sim = PrescribedRpmConfig(
            dt_s=dt_s,
            t_end_s=t_end_s,
            rpm_mode="constant",
            constant_rpm=constant_rpm,
        )
        states = run_prescribed_rpm_physics(config, prop_entry, sim=sim)
        metrics = analyze_physics_stability(
            states,
            config,
            case_id=f"dt_sensitivity_dt{dt_s:g}",
            rpm_profile=f"constant_{constant_rpm:g}",
            dt_s=dt_s,
        )
        results.append(metrics)
        final_thetas.append(metrics.theta_final_deg)

    if final_thetas:
        theta_span = max(final_thetas) - min(final_thetas)
        sensitive = theta_span > 2.0
        if sensitive:
            note = (
                f"dt sensitivity: theta_final span={theta_span:.3f} deg "
                f"across dt={list(dt_values)}"
            )
            return [
                replace(m, numerical_sensitivity_flag=True, notes=note) for m in results
            ]

    return results


def run_hinge_parameter_diagnostic_sweep(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    constant_rpm: float = 7100.0,
) -> list[dict[str, str | float | bool]]:
    """Small diagnostic sweep over stiffness, damping, and aero gain multipliers."""
    stiffness_mults = (0.25, 0.5, 1.0)
    damping_mults = (1.0, 2.0, 5.0)
    aero_mults = (1.0, 2.0, 5.0)
    rows: list[dict[str, str | float | bool]] = []

    for k_mult in stiffness_mults:
        for c_mult in damping_mults:
            for a_mult in aero_mults:
                cfg = scaled_hinge_config(
                    config,
                    stiffness_multiplier=k_mult,
                    damping_multiplier=c_mult,
                    aero_gain_multiplier=a_mult,
                )
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
                    case_id=f"sweep_k{k_mult}_c{c_mult}_a{a_mult}",
                    rpm_profile=f"constant_{constant_rpm:g}",
                    dt_s=dt_s,
                )
                rows.append(
                    {
                        "case_id": metrics.case_id,
                        "stiffness_multiplier": k_mult,
                        "damping_multiplier": c_mult,
                        "aero_gain_multiplier": a_mult,
                        "theta_final_deg": metrics.theta_final_deg,
                        "D_aero_final_m": metrics.D_aero_final_m,
                        "thrust_tip_final_n": metrics.thrust_tip_final_n,
                        "chattering_flag": metrics.chattering_flag,
                        "stable_flag": metrics.stable_flag,
                    }
                )
    return rows


def quasi_static_equilibrium_theta_deg(
    rpm: float,
    config: FoldablePropellerConfig,
) -> float | None:
    """Algebraic equilibrium theta where M_cent approx M_stiff (no dynamics)."""
    if rpm <= 0.0:
        return config.hinge.theta_min_deg
    hinge = config.hinge
    span = hinge.theta_max_deg - hinge.theta_min_deg
    if span <= 0.0:
        return hinge.theta_max_deg

    # Bisection on theta in [theta_min, theta_max]
    lo = hinge.theta_min_deg
    hi = hinge.theta_max_deg

    def imbalance(theta_deg: float) -> float:
        return centrifugal_moment_nm(rpm, theta_deg, config) - stiffness_moment_nm(
            theta_deg, config
        )

    imb_lo = imbalance(lo)
    imb_hi = imbalance(hi)
    if imb_lo <= 0.0:
        return lo
    if imb_hi >= 0.0:
        return hi

    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if imbalance(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
