"""CFD/BEM preparation export for foldable V2 (input data only — not CFD results)."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pythrust.propellers.database import PropellerEntry

from ..geometry_helpers import root_diameter_m
from ..models import FoldablePropellerConfig
from .motor_coupled_performance import (
    CASE_SPEC_BY_ID,
    DEFAULT_TARGET_CHECKPOINT_RPM,
    MOTOR_COUPLING_LEVEL,
    MOTOR_COUPLED_EVALUATION_CASES,
    CaseVariantBinding,
    MotorCoupled7100InterpolatedRow,
    resolve_variant_config,
    run_motor_coupled_7100rpm_interpolated_v2,
    run_motor_coupled_foldable_performance_v2,
)

CFD_PREP_OUTPUT_DIR = "outputs/foldable/cfd_prep"
CFD_STATUS_NOTE = (
    "NOT CFD RESULT — V2 model preparation export for future "
    "Ansys Fluent / OpenFOAM / BEM validation only"
)
THRUST_REFERENCE_BASIS = "calibrated_pretest_70_fixed_model_proxy"
TORQUE_REFERENCE_BASIS = "foldable_proxy_quasi_steady_aero_at_D_aero"
DEFAULT_RHO_KG_M3 = 1.225

CFD_OPERATING_POINTS_V2_COLUMNS: tuple[str, ...] = (
    "case_id",
    "variant_id",
    "rpm",
    "omega_rad_s",
    "theta_deg",
    "D_root_m",
    "D_aero_m",
    "D_open_m",
    "tip_ratio",
    "root_ratio",
    "T_pretest_n",
    "T_target_n",
    "aero_torque_nm",
    "motor_torque_nm",
    "motor_torque_margin_nm",
    "current_a",
    "power_w",
    "thrust_reference_basis",
    "torque_reference_basis",
    "cfd_status_note",
)

CFD_GEOMETRY_PARAMETERS_V2_COLUMNS: tuple[str, ...] = (
    "case_id",
    "variant_id",
    "root_segment_length_m",
    "tip_segment_length_m",
    "hinge_radius_m",
    "tip_segment_cg_from_hinge_m",
    "stowed_envelope_diameter_m",
    "open_diameter_m",
    "theta_min_deg",
    "theta_final_deg",
    "deployment_bias_angle_deg",
    "latch_required_flag",
    "expected_open_state",
    "cfd_status_note",
)

CFD_CASE_RECOMMENDATIONS_V2_COLUMNS: tuple[str, ...] = (
    "priority",
    "case_id",
    "variant_id",
    "purpose",
    "expected_result",
    "comparison_target",
    "use_in_report_flag",
)

CFD_READINESS_AUDIT_V2_COLUMNS: tuple[str, ...] = (
    "check_id",
    "status",
    "value",
    "expected_behavior",
    "note",
)

CFD_CASE_RECOMMENDATIONS: tuple[tuple[int, str, str], ...] = (
    (1, "fixed_25cm_reference", "TIP_HINGED_250_V02"),
    (2, "root_only_20cm", "TIP_HINGED_250_V02"),
    (3, "latch_theta0", "TIP_HINGED_250_V02"),
    (4, "bias10_k0.25_s5", "TIP_HINGED_250_RT65_35"),
    (5, "bias5_k0.25_s5", "TIP_HINGED_250_V02"),
)


@dataclass(frozen=True)
class CfdOperatingPointRow:
    case_id: str
    variant_id: str
    rpm: float
    omega_rad_s: float
    theta_deg: float
    D_root_m: float
    D_aero_m: float
    D_open_m: float
    tip_ratio: int
    root_ratio: int
    T_pretest_n: float
    T_target_n: float
    aero_torque_nm: float | None
    motor_torque_nm: float
    motor_torque_margin_nm: float | None
    current_a: float
    power_w: float
    thrust_reference_basis: str
    torque_reference_basis: str
    cfd_status_note: str

    def to_csv_row(self) -> dict[str, str | float]:
        return {
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "rpm": self.rpm,
            "omega_rad_s": self.omega_rad_s,
            "theta_deg": self.theta_deg,
            "D_root_m": self.D_root_m,
            "D_aero_m": self.D_aero_m,
            "D_open_m": self.D_open_m,
            "tip_ratio": self.tip_ratio,
            "root_ratio": self.root_ratio,
            "T_pretest_n": self.T_pretest_n,
            "T_target_n": self.T_target_n,
            "aero_torque_nm": self._optional_float(self.aero_torque_nm),
            "motor_torque_nm": self.motor_torque_nm,
            "motor_torque_margin_nm": self._optional_float(self.motor_torque_margin_nm),
            "current_a": self.current_a,
            "power_w": self.power_w,
            "thrust_reference_basis": self.thrust_reference_basis,
            "torque_reference_basis": self.torque_reference_basis,
            "cfd_status_note": self.cfd_status_note,
        }

    @staticmethod
    def _optional_float(value: float | None) -> str | float:
        if value is None:
            return ""
        return value


@dataclass(frozen=True)
class CfdGeometryParametersRow:
    case_id: str
    variant_id: str
    root_segment_length_m: float
    tip_segment_length_m: float
    hinge_radius_m: float
    tip_segment_cg_from_hinge_m: float
    stowed_envelope_diameter_m: float
    open_diameter_m: float
    theta_min_deg: float
    theta_final_deg: float
    deployment_bias_angle_deg: float
    latch_required_flag: bool
    expected_open_state: str
    cfd_status_note: str

    def to_csv_row(self) -> dict[str, str | float | bool]:
        return {
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "root_segment_length_m": self.root_segment_length_m,
            "tip_segment_length_m": self.tip_segment_length_m,
            "hinge_radius_m": self.hinge_radius_m,
            "tip_segment_cg_from_hinge_m": self.tip_segment_cg_from_hinge_m,
            "stowed_envelope_diameter_m": self.stowed_envelope_diameter_m,
            "open_diameter_m": self.open_diameter_m,
            "theta_min_deg": self.theta_min_deg,
            "theta_final_deg": self.theta_final_deg,
            "deployment_bias_angle_deg": self.deployment_bias_angle_deg,
            "latch_required_flag": self.latch_required_flag,
            "expected_open_state": self.expected_open_state,
            "cfd_status_note": self.cfd_status_note,
        }


@dataclass(frozen=True)
class CfdCaseRecommendationRow:
    priority: int
    case_id: str
    variant_id: str
    purpose: str
    expected_result: str
    comparison_target: str
    use_in_report_flag: bool

    def to_csv_row(self) -> dict[str, str | int | bool]:
        return {
            "priority": self.priority,
            "case_id": self.case_id,
            "variant_id": self.variant_id,
            "purpose": self.purpose,
            "expected_result": self.expected_result,
            "comparison_target": self.comparison_target,
            "use_in_report_flag": self.use_in_report_flag,
        }


@dataclass(frozen=True)
class CfdReadinessAuditRow:
    check_id: str
    status: str
    value: str
    expected_behavior: str
    note: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "value": self.value,
            "expected_behavior": self.expected_behavior,
            "note": self.note,
        }


def _root_tip_ratios_from_config(config: FoldablePropellerConfig) -> tuple[int, int]:
    open_radius_m = config.geometry.diameter_open_m / 2.0
    if open_radius_m <= 0.0:
        return 0, 0
    root_ratio = int(round(100.0 * config.geometry.hinge_position_m / open_radius_m))
    root_ratio = max(0, min(100, root_ratio))
    return root_ratio, 100 - root_ratio


def _expected_open_state(case_id: str, theta_deg: float, latch: bool) -> str:
    if case_id == "root_only_20cm":
        return "stowed_root_only"
    if case_id == "fixed_25cm_reference":
        return "full_open_reference_geometry"
    if latch:
        return "latched_open_stop"
    if abs(theta_deg) < 5.0:
        return "near_full_open_equilibrium"
    return "partial_deployment_equilibrium"


def _case_geometry_controls(case_id: str) -> tuple[float, bool]:
    spec = CASE_SPEC_BY_ID.get(case_id)
    if spec is None or len(spec) == 2:
        return 0.0, False
    _, bias, _k, _scale, _offset, latch = spec  # type: ignore[misc]
    return float(bias), bool(latch)


def _ratio_for_recommendation(
    case_id: str,
    variant_id: str,
) -> tuple[int, int] | None:
    for variant, case, ratio in MOTOR_COUPLED_EVALUATION_CASES:
        if variant == variant_id and case == case_id:
            return ratio
    if variant_id == "TIP_HINGED_250_RT65_35":
        return (65, 35)
    return None


def cfd_case_recommendations_bindings() -> tuple[CaseVariantBinding, ...]:
    return tuple(
        (variant_id, case_id, _ratio_for_recommendation(case_id, variant_id))
        for _priority, case_id, variant_id in CFD_CASE_RECOMMENDATIONS
    )


def _interpolated_row_for_case(
    rows: Sequence[MotorCoupled7100InterpolatedRow],
    *,
    case_id: str,
    variant_id: str,
) -> MotorCoupled7100InterpolatedRow | None:
    for row in rows:
        if row.case_id == case_id and row.variant_id == variant_id:
            return row
    return None


def build_cfd_operating_points_v2(
    interpolated_rows: Sequence[MotorCoupled7100InterpolatedRow],
    base_config: FoldablePropellerConfig,
    *,
    case_bindings: Sequence[CaseVariantBinding] | None = None,
) -> list[CfdOperatingPointRow]:
    """Build CFD operating-point table from motor-coupled 7100 rpm interpolation."""
    bindings = case_bindings or cfd_case_recommendations_bindings()
    points: list[CfdOperatingPointRow] = []
    for variant_id, case_id, ratio in bindings:
        row = _interpolated_row_for_case(
            interpolated_rows, case_id=case_id, variant_id=variant_id
        )
        if row is None:
            continue
        config = resolve_variant_config(base_config, variant_id, ratio)
        d_root = root_diameter_m(config.geometry)
        root_ratio, tip_ratio = _root_tip_ratios_from_config(config)
        omega = row.rpm * math.pi / 30.0
        points.append(
            CfdOperatingPointRow(
                case_id=case_id,
                variant_id=variant_id,
                rpm=row.rpm,
                omega_rad_s=omega,
                theta_deg=row.theta_final_deg,
                D_root_m=d_root,
                D_aero_m=row.D_aero_m,
                D_open_m=config.geometry.diameter_open_m,
                tip_ratio=tip_ratio,
                root_ratio=root_ratio,
                T_pretest_n=row.T_total_pretest_fixed_n,
                T_target_n=row.T_total_target_fixed_n,
                aero_torque_nm=row.aero_torque_nm,
                motor_torque_nm=row.motor_torque_nm,
                motor_torque_margin_nm=row.motor_torque_margin_nm,
                current_a=row.current_a,
                power_w=row.power_w,
                thrust_reference_basis=THRUST_REFERENCE_BASIS,
                torque_reference_basis=TORQUE_REFERENCE_BASIS,
                cfd_status_note=CFD_STATUS_NOTE,
            )
        )
    return points


def build_cfd_geometry_parameters_v2(
    interpolated_rows: Sequence[MotorCoupled7100InterpolatedRow],
    base_config: FoldablePropellerConfig,
    *,
    case_bindings: Sequence[CaseVariantBinding] | None = None,
) -> list[CfdGeometryParametersRow]:
    """Build per-case geometry parameter rows for CFD meshing prep."""
    bindings = case_bindings or cfd_case_recommendations_bindings()
    geometry_rows: list[CfdGeometryParametersRow] = []
    for variant_id, case_id, ratio in bindings:
        row = _interpolated_row_for_case(
            interpolated_rows, case_id=case_id, variant_id=variant_id
        )
        if row is None:
            continue
        config = resolve_variant_config(base_config, variant_id, ratio)
        geom = config.geometry
        bias_deg, latch = _case_geometry_controls(case_id)
        geometry_rows.append(
            CfdGeometryParametersRow(
                case_id=case_id,
                variant_id=variant_id,
                root_segment_length_m=geom.main_blade_length_m,
                tip_segment_length_m=geom.tip_segment_length_m,
                hinge_radius_m=geom.hinge_position_m,
                tip_segment_cg_from_hinge_m=geom.tip_segment_cg_from_hinge_m,
                stowed_envelope_diameter_m=geom.stowed_envelope_diameter_m,
                open_diameter_m=geom.diameter_open_m,
                theta_min_deg=config.hinge.theta_min_deg,
                theta_final_deg=row.theta_final_deg,
                deployment_bias_angle_deg=bias_deg,
                latch_required_flag=latch,
                expected_open_state=_expected_open_state(
                    case_id, row.theta_final_deg, latch
                ),
                cfd_status_note=CFD_STATUS_NOTE,
            )
        )
    return geometry_rows


def build_cfd_case_recommendations_v2() -> list[CfdCaseRecommendationRow]:
    purpose_by_case = {
        "fixed_25cm_reference": (
            "Upper-bound reference propeller at checkpoint rpm",
            "Match APC 10x4.7SF scaled thrust ~9.10 N at 7100 rpm",
            "APC database / thrust stand if available",
            True,
        ),
        "root_only_20cm": (
            "Compact stowed-root lower bound",
            "Root-segment-only thrust ~3.73 N at 7100 rpm",
            "Compact 20 cm baseline in V2 model",
            True,
        ),
        "latch_theta0": (
            "Primary foldable latched open-stop candidate",
            "Calibrated pretest thrust ~6.37 N (~70% of 25 cm ref)",
            "Engineering design report latch reference",
            True,
        ),
        "bias10_k0.25_s5": (
            "Best no-latch RT65_35 geometry candidate",
            "Match latch pretest thrust with alternate root/tip ratio",
            "latch_theta0 at 7100 rpm",
            True,
        ),
        "bias5_k0.25_s5": (
            "Best no-latch V02 geometry candidate",
            "Near-latch pretest thrust on baseline variant",
            "latch_theta0 at 7100 rpm",
            False,
        ),
    }
    rows: list[CfdCaseRecommendationRow] = []
    for priority, case_id, variant_id in CFD_CASE_RECOMMENDATIONS:
        purpose, expected, comparison, report_flag = purpose_by_case[case_id]
        rows.append(
            CfdCaseRecommendationRow(
                priority=priority,
                case_id=case_id,
                variant_id=variant_id,
                purpose=purpose,
                expected_result=expected,
                comparison_target=comparison,
                use_in_report_flag=report_flag,
            )
        )
    return rows


def build_cfd_readiness_audit_v2(
    operating_points: Sequence[CfdOperatingPointRow],
    geometry_rows: Sequence[CfdGeometryParametersRow],
    *,
    cad_stl_path: Path | None = None,
    mesh_path: Path | None = None,
) -> list[CfdReadinessAuditRow]:
    """Audit whether V2 model exports are ready for external CFD setup."""
    audits: list[CfdReadinessAuditRow] = []

    rpm_ok = all(abs(row.rpm - DEFAULT_TARGET_CHECKPOINT_RPM) < 1.0 for row in operating_points)
    audits.append(
        CfdReadinessAuditRow(
            check_id="operating_rpm_exists",
            status="pass" if rpm_ok and operating_points else "fail",
            value=f"{len(operating_points)} rows @ {DEFAULT_TARGET_CHECKPOINT_RPM:.0f} rpm",
            expected_behavior="All CFD prep operating points at 7100 rpm checkpoint",
            note=CFD_STATUS_NOTE,
        )
    )

    geom_ok = len(geometry_rows) == len(operating_points) and all(
        row.root_segment_length_m > 0.0 for row in geometry_rows
    )
    audits.append(
        CfdReadinessAuditRow(
            check_id="geometry_parameters_exist",
            status="pass" if geom_ok else "fail",
            value=str(len(geometry_rows)),
            expected_behavior="Geometry parameter row per operating case",
            note="From FoldablePropellerConfig + deployment state",
        )
    )

    theta_ok = len(operating_points) > 0 and all(
        math.isfinite(row.theta_deg) for row in operating_points
    )
    audits.append(
        CfdReadinessAuditRow(
            check_id="theta_value_exists",
            status="pass" if theta_ok else "fail",
            value="present" if theta_ok else "missing",
            expected_behavior="Final hinge angle exported for each case",
            note="theta_deg from prescribed-RPM deployment equilibrium",
        )
    )

    d_aero_ok = all(row.D_aero_m > 0.0 for row in operating_points)
    audits.append(
        CfdReadinessAuditRow(
            check_id="D_aero_exists",
            status="pass" if d_aero_ok else "fail",
            value="present" if d_aero_ok else "missing",
            expected_behavior="Aerodynamic effective diameter for each case",
            note="D_aero_m blends root and tip contribution",
        )
    )

    torque_ok = any(
        row.aero_torque_nm is not None and row.aero_torque_nm > 0.0
        for row in operating_points
    )
    audits.append(
        CfdReadinessAuditRow(
            check_id="torque_estimate_exists",
            status="pass" if torque_ok else "fail",
            value="foldable_proxy" if torque_ok else "missing",
            expected_behavior="Quasi-steady aero torque proxy at D_aero",
            note="NOT measured CFD torque — model proxy only",
        )
    )

    thrust_ok = all(row.T_pretest_n > 0.0 for row in operating_points)
    audits.append(
        CfdReadinessAuditRow(
            check_id="thrust_estimate_exists",
            status="pass" if thrust_ok else "fail",
            value="calibrated_pretest" if thrust_ok else "missing",
            expected_behavior="Calibrated pretest thrust target for comparison",
            note="NOT measured CFD thrust — model proxy only",
        )
    )

    audits.append(
        CfdReadinessAuditRow(
            check_id="motor_coupling_level_documented",
            status="pass",
            value=MOTOR_COUPLING_LEVEL,
            expected_behavior="Coupling limitation documented for CFD interpretation",
            note="Foldable load not yet fed back into PyThrust solver",
        )
    )

    cad_exists = cad_stl_path is not None and cad_stl_path.is_file()
    audits.append(
        CfdReadinessAuditRow(
            check_id="cad_stl_availability",
            status="not_available",
            value="placeholder_only" if not cad_exists else str(cad_stl_path),
            expected_behavior="CAD/STL not required for Level-1 prep export",
            note=(
                "No CAD/STL generated in this phase; geometry CSV is parametric placeholder"
            ),
        )
    )

    mesh_exists = mesh_path is not None and mesh_path.is_file()
    audits.append(
        CfdReadinessAuditRow(
            check_id="mesh_status",
            status="not_available",
            value="not_generated" if not mesh_exists else str(mesh_path),
            expected_behavior="Volume mesh created in external CFD tool",
            note="Mesh generation is out of scope for V2 prep layer",
        )
    )

    audits.append(
        CfdReadinessAuditRow(
            check_id="experimental_validation_status",
            status="not_available",
            value="none",
            expected_behavior="Thrust stand / PIV validation after CFD setup",
            note="No experimental dataset linked to this export",
        )
    )

    return audits


def format_cfd_boundary_condition_notes(
    *,
    rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    rho_kg_m3: float = DEFAULT_RHO_KG_M3,
) -> str:
    omega = rpm * math.pi / 30.0
    return f"""# CFD Boundary Condition Notes — Foldable V2 (Preparation Only)

> **{CFD_STATUS_NOTE}**

This document suggests boundary conditions for a future Ansys Fluent or OpenFOAM study.
No CFD simulation has been run in the PyThrust repository.

## Fluid properties

| Parameter | Value | Note |
|-----------|-------|------|
| Air density ρ | {rho_kg_m3} kg/m³ | ISA sea-level approximation |
| Temperature | 15 °C (optional) | Match wind-tunnel if available |
| Viscosity | Sutherland / ideal air | Standard Fluent/OpenFOAM air model |

## Rotational operating point

| Parameter | Value |
|-----------|-------|
| Checkpoint RPM | {rpm:.0f} rpm |
| Angular velocity ω | {omega:.2f} rad/s |
| Advance ratio J | 0 (hover static thrust) |

## Domain and boundary setup (suggested)

1. **Far-field:** pressure outlet or entrainment boundary at ≥ 5–10 D downstream/upstream.
2. **Inlet:** velocity inlet at zero freestream for hover, or symmetry plane for half-domain.
3. **Ground:** optional wall or symmetry depending on test stand geometry.
4. **Propeller region:** rotating cell zone (MRF) or sliding mesh interface.

## Rotating domain

- **First steady approximation:** Multiple Reference Frame (MRF) with single rotational speed ω.
  - Sufficient for time-averaged thrust/torque at fixed deployment angle θ.
  - Align rotation axis with motor shaft; use `{rpm:.0f}` rpm from V2 checkpoint export.
- **Sliding mesh / transient:** Required when:
  - Hinge deployment during spin-up is modeled.
  - Tip segment motion relative to root must be resolved in time.
  - Blade passage unsteadiness or latch contact dynamics matter.

**Why MRF is enough first:** Current V2 export fixes θ and D_aero at equilibrium;
a steady actuator-disk or MRF propeller model can be compared against
`cfd_operating_points_v2.csv` thrust/torque proxies before investing in sliding mesh.

## Wall and no-slip

- Blade surfaces: no-slip wall, roughness default smooth unless manufacturing data exists.
- Hub and hinge hardware: no-slip; simplify geometry in Level-1 if CAD unavailable.
- Tip gap and latch clearance: document as uncertainty band in first CFD pass.

## Thrust and torque extraction

- **Thrust:** integrate pressure + viscous force on blade/hub surfaces along motor axis.
- **Torque:** moment about rotation axis on blade surfaces (exclude motor shaft friction).
- **Compare to:** `T_pretest_n`, `aero_torque_nm` in `cfd_operating_points_v2.csv`
  (model proxies, not experimental truth).

## Limitations

- Export uses **effective diameter** and **fixed θ**; real foldable CFD needs multi-body CAD.
- Calibrated thrust factors are **not** CFD inputs — compare CFD raw thrust to model afterward.
- Motor coupling is `reference_load_postprocess`; coupled aero-motor iteration is future work.
- No CAD/STL or mesh is included in Level-1 prep; parametric geometry CSV only.

## Recommended external workflow

1. Import geometry parameters from `cfd_geometry_parameters_v2.csv`.
2. Build or import CAD (Level 3) — placeholder until mechanical design frozen.
3. Steady MRF hover run at {rpm:.0f} rpm for each priority case in
   `cfd_case_recommendations_v2.csv`.
4. Compare integrated thrust/torque to operating-point CSV.
5. Proceed to sliding mesh only if deployment transient is in scope.
"""


def run_cfd_preparation_v2(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    output_dir: str | Path,
    target_rpm: float = DEFAULT_TARGET_CHECKPOINT_RPM,
    dt_s: float = 0.001,
    t_end_s: float = 2.0,
    cad_stl_path: Path | None = None,
    mesh_path: Path | None = None,
) -> dict[str, Path]:
    """Generate all CFD preparation artifacts under output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    perf_rows = run_motor_coupled_foldable_performance_v2(
        base_config,
        prop_entry,
        evaluation_cases=MOTOR_COUPLED_EVALUATION_CASES,
        target_checkpoint_rpm=target_rpm,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=target_rpm,
    )
    interpolated = run_motor_coupled_7100rpm_interpolated_v2(
        base_config,
        prop_entry,
        perf_rows,
        target_rpm=target_rpm,
        dt_s=dt_s,
        t_end_s=t_end_s,
        constant_rpm=target_rpm,
    )

    bindings = cfd_case_recommendations_bindings()
    operating = build_cfd_operating_points_v2(interpolated, base_config, case_bindings=bindings)
    geometry = build_cfd_geometry_parameters_v2(
        interpolated, base_config, case_bindings=bindings
    )
    recommendations = build_cfd_case_recommendations_v2()
    audit = build_cfd_readiness_audit_v2(
        operating, geometry, cad_stl_path=cad_stl_path, mesh_path=mesh_path
    )

    paths: dict[str, Path] = {}
    paths["operating_points"] = out / "cfd_operating_points_v2.csv"
    paths["geometry"] = out / "cfd_geometry_parameters_v2.csv"
    paths["recommendations"] = out / "cfd_case_recommendations_v2.csv"
    paths["audit"] = out / "cfd_readiness_audit_v2.csv"
    paths["boundary_notes"] = out / "cfd_boundary_condition_notes.md"

    write_cfd_operating_points_v2_csv(paths["operating_points"], operating)
    write_cfd_geometry_parameters_v2_csv(paths["geometry"], geometry)
    write_cfd_case_recommendations_v2_csv(paths["recommendations"], recommendations)
    write_cfd_readiness_audit_v2_csv(paths["audit"], audit)
    paths["boundary_notes"].write_text(
        format_cfd_boundary_condition_notes(rpm=target_rpm),
        encoding="utf-8",
    )
    return paths


def write_cfd_operating_points_v2_csv(
    path: str | Path,
    rows: Sequence[CfdOperatingPointRow],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CFD_OPERATING_POINTS_V2_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_cfd_geometry_parameters_v2_csv(
    path: str | Path,
    rows: Sequence[CfdGeometryParametersRow],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(CFD_GEOMETRY_PARAMETERS_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_cfd_case_recommendations_v2_csv(
    path: str | Path,
    rows: Sequence[CfdCaseRecommendationRow],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(CFD_CASE_RECOMMENDATIONS_V2_COLUMNS)
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def write_cfd_readiness_audit_v2_csv(
    path: str | Path,
    rows: Sequence[CfdReadinessAuditRow],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CFD_READINESS_AUDIT_V2_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())
