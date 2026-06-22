"""Engineering design report generation for foldable V2 (documentation layer only)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .dynamics.motor_coupled_performance import (
    MOTOR_COUPLING_LEVEL,
    SOLVER_LOAD_NOTE,
)

REPORT_DIR_NAME = "foldable_v2_engineering_design"
MAIN_REPORT_NAME = "foldable_v2_engineering_design_report.md"
KEY_RESULTS_NAME = "report_key_results.csv"
FIGURE_INDEX_NAME = "figure_index.md"
ASSUMPTIONS_NAME = "model_assumptions_and_limits.md"
CONCLUSION_TR_NAME = "report_conclusion_tr.md"

DEFAULT_FOLDABLE_PRETEST_CASE = "latch_theta0"
DEFAULT_FOLDABLE_PRETEST_VARIANT = "TIP_HINGED_250_V02"

REPORT_KEY_RESULTS_COLUMNS: tuple[str, ...] = (
    "metric",
    "value",
    "unit",
    "interpretation",
)

FIGURE_CATALOG: tuple[tuple[str, str, bool, str], ...] = (
    (
        "outputs/foldable/dynamics/physics/figures/constant_7100_thrust_split.png",
        "V2 prescribed-RPM thrust split at 7100 rpm checkpoint",
        True,
        "Use with note that values are model-based, not measured.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/constant_7100_phase_portrait.png",
        "Hinge angle vs angular velocity at constant 7100 rpm",
        True,
        "Illustrates deployment equilibrium; single reference case.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/constant_7100_diameter_geo_aero.png",
        "Geometric vs aerodynamic effective diameter at 7100 rpm",
        True,
        "Shows D_geo and D_aero separation in V2 model.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/constant_7100_hinge_kinematics.png",
        "Hinge kinematics time history at 7100 rpm",
        True,
        "Prescribed-RPM diagnostic; not motor-coupled transient.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/constant_7100_moments.png",
        "Hinge moment balance at 7100 rpm",
        True,
        "Moment-based deployment model visualization.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/diag_bias10_thrust_split.png",
        "Deployment diagnostic thrust split (bias10 case)",
        True,
        "Candidate geometry; compare with latch reference.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/diag_bias10_phase_portrait.png",
        "Deployment diagnostic phase portrait (bias10)",
        True,
        "Partial deployment state; not full latch open-stop.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/ramp_thrust_split.png",
        "Spin-up ramp thrust split",
        False,
        "Dynamic V1 layer; do not mix directly with V2 motor-coupled tables.",
    ),
    (
        "outputs/foldable/dynamics/physics/figures/ramp_phase_portrait.png",
        "Spin-up ramp phase portrait",
        False,
        "Transient startup; different coupling level than 7100 checkpoint.",
    ),
    (
        "outputs/foldable/figures/foldable_thrust_n_vs_throttle_by_variant.png",
        "Design-variant thrust vs throttle sweep",
        False,
        "Pre-motor-coupled design sweep; throttle axis not V2 motor equilibrium.",
    ),
    (
        "outputs/foldable/figures/effective_diameter_m_vs_throttle_by_variant.png",
        "Effective diameter vs throttle by variant",
        False,
        "Design-variant layer; verify variant ID before citing in V2 report.",
    ),
    (
        "outputs/foldable/figures/theta_deg_vs_throttle_by_variant.png",
        "Hinge angle vs throttle by variant",
        False,
        "Design-variant sweep; moment model version may differ from V02 config.",
    ),
    (
        "outputs/foldable/figures/thrust_difference_percent_vs_throttle_by_variant.png",
        "Thrust difference vs fixed reference propeller",
        False,
        "Normalized against APC reference; not calibrated pretest split.",
    ),
    (
        "outputs/foldable/figures/fig_thrust_difference_normalized_250mm.png",
        "Normalized thrust loss vs 250 mm reference",
        False,
        "Summary metric for variant ranking, not final V2 motor checkpoint.",
    ),
    (
        "outputs/foldable/figures/flight_startup_scores_by_variant.png",
        "Variant decision support scores",
        False,
        "Decision-support only; not experimental validation.",
    ),
    (
        "outputs/foldable/dynamics/figures/spinup_RT75_25_step_report.png",
        "Step-throttle spin-up report figure",
        False,
        "Ideal step throttle; not interpolated 7100 rpm operating point.",
    ),
    (
        "outputs/foldable/dynamics/figures/spinup_RT75_25_ramp_report.png",
        "Ramp-throttle spin-up report figure",
        False,
        "Transient model; coupling level differs from reference_load_postprocess.",
    ),
)


@dataclass(frozen=True)
class ReportKeyResult:
    metric: str
    value: str
    unit: str
    interpretation: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True)
class EngineeringReportMetrics:
    root_only_20cm_thrust_7100: float
    foldable_pretest_thrust_7100: float
    fixed_25cm_reference_thrust_7100: float
    gain_vs_compact_20cm_root_percent: float
    loss_vs_25cm_reference_percent: float
    interpolated_throttle_7100: float
    motor_current_7100: float
    motor_power_7100: float
    aero_torque_root_20cm: float
    aero_torque_foldable: float
    motor_torque_margin_foldable_nm: float
    motor_torque_margin_foldable_percent: float
    motor_coupling_level: str


def _read_interpolated_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _find_row(
    rows: Sequence[dict[str, str]],
    *,
    case_id: str,
    variant_id: str | None = None,
) -> dict[str, str] | None:
    for row in rows:
        if row.get("case_id") != case_id:
            continue
        if variant_id is not None and row.get("variant_id") != variant_id:
            continue
        return row
    return None


def _float_field(row: dict[str, str], key: str, default: float = 0.0) -> float:
    raw = row.get(key, "")
    if raw in ("", None):
        return default
    return float(raw)


def load_engineering_report_metrics(
    interpolated_csv_path: str | Path,
    *,
    foldable_case_id: str = DEFAULT_FOLDABLE_PRETEST_CASE,
    foldable_variant_id: str = DEFAULT_FOLDABLE_PRETEST_VARIANT,
) -> EngineeringReportMetrics:
    """Load checkpoint metrics from motor-coupled interpolated CSV."""
    rows = _read_interpolated_csv(Path(interpolated_csv_path))
    if not rows:
        raise FileNotFoundError(
            f"Motor-coupled interpolated CSV not found or empty: {interpolated_csv_path}"
        )

    root = _find_row(rows, case_id="root_only_20cm")
    ref = _find_row(rows, case_id="fixed_25cm_reference")
    foldable = _find_row(
        rows,
        case_id=foldable_case_id,
        variant_id=foldable_variant_id,
    )
    if root is None or ref is None or foldable is None:
        raise ValueError(
            "Interpolated CSV missing required rows: "
            "root_only_20cm, fixed_25cm_reference, foldable pretest candidate"
        )

    root_thrust = _float_field(root, "T_total_pretest_fixed_n")
    foldable_thrust = _float_field(foldable, "T_total_pretest_fixed_n")
    ref_thrust = _float_field(ref, "T_total_pretest_fixed_n")
    gain_compact = _float_field(foldable, "gain_vs_compact_root_20cm_percent")
    loss = (
        100.0 * (ref_thrust - foldable_thrust) / ref_thrust if ref_thrust > 0.0 else 0.0
    )

    return EngineeringReportMetrics(
        root_only_20cm_thrust_7100=root_thrust,
        foldable_pretest_thrust_7100=foldable_thrust,
        fixed_25cm_reference_thrust_7100=ref_thrust,
        gain_vs_compact_20cm_root_percent=gain_compact,
        loss_vs_25cm_reference_percent=loss,
        interpolated_throttle_7100=_float_field(foldable, "interpolated_throttle"),
        motor_current_7100=_float_field(foldable, "current_a"),
        motor_power_7100=_float_field(foldable, "power_w"),
        aero_torque_root_20cm=_float_field(root, "aero_torque_nm"),
        aero_torque_foldable=_float_field(foldable, "aero_torque_nm"),
        motor_torque_margin_foldable_nm=_float_field(foldable, "motor_torque_margin_nm"),
        motor_torque_margin_foldable_percent=_float_field(
            foldable, "motor_torque_margin_percent"
        ),
        motor_coupling_level=foldable.get("motor_coupling_level", MOTOR_COUPLING_LEVEL),
    )


def build_report_key_results(metrics: EngineeringReportMetrics) -> list[ReportKeyResult]:
    return [
        ReportKeyResult(
            metric="root_only_20cm_thrust_7100",
            value=f"{metrics.root_only_20cm_thrust_7100:.2f}",
            unit="N",
            interpretation="Compact stowed-root baseline at interpolated 7100 rpm",
        ),
        ReportKeyResult(
            metric="foldable_pretest_thrust_7100",
            value=f"{metrics.foldable_pretest_thrust_7100:.2f}",
            unit="N",
            interpretation="Calibrated pretest_70_fixed foldable thrust at 7100 rpm",
        ),
        ReportKeyResult(
            metric="fixed_25cm_reference_thrust_7100",
            value=f"{metrics.fixed_25cm_reference_thrust_7100:.2f}",
            unit="N",
            interpretation="Full 25 cm reference propeller thrust at checkpoint rpm",
        ),
        ReportKeyResult(
            metric="gain_vs_compact_20cm_root",
            value=f"{metrics.gain_vs_compact_20cm_root_percent:.1f}",
            unit="percent",
            interpretation="Primary reporting gain; compact-root compact root baseline",
        ),
        ReportKeyResult(
            metric="loss_vs_25cm_reference",
            value=f"{metrics.loss_vs_25cm_reference_percent:.1f}",
            unit="percent",
            interpretation="Thrust deficit vs fixed 25 cm reference at same rpm",
        ),
        ReportKeyResult(
            metric="interpolated_throttle_7100",
            value=f"{metrics.interpolated_throttle_7100:.3f}",
            unit="dimensionless",
            interpretation="Throttle required to reach 7100 rpm in motor-coupled sweep",
        ),
        ReportKeyResult(
            metric="motor_current_7100",
            value=f"{metrics.motor_current_7100:.1f}",
            unit="A",
            interpretation="Interpolated battery current at 7100 rpm checkpoint",
        ),
        ReportKeyResult(
            metric="motor_power_7100",
            value=f"{metrics.motor_power_7100:.0f}",
            unit="W",
            interpretation="Interpolated electrical power at 7100 rpm checkpoint",
        ),
        ReportKeyResult(
            metric="aero_torque_root_20cm",
            value=f"{metrics.aero_torque_root_20cm:.4f}",
            unit="Nm",
            interpretation="Post-processed foldable_proxy aero torque at D=0.20 m",
        ),
        ReportKeyResult(
            metric="aero_torque_foldable",
            value=f"{metrics.aero_torque_foldable:.4f}",
            unit="Nm",
            interpretation="Post-processed foldable_proxy aero torque at deployed D_aero",
        ),
        ReportKeyResult(
            metric="motor_torque_margin_foldable",
            value=(
                f"{metrics.motor_torque_margin_foldable_nm:.4f} "
                f"({metrics.motor_torque_margin_foldable_percent:.1f}%)"
            ),
            unit="Nm",
            interpretation="Motor torque minus foldable aero torque at 7100 rpm",
        ),
        ReportKeyResult(
            metric="motor_coupling_level",
            value=metrics.motor_coupling_level,
            unit="label",
            interpretation=SOLVER_LOAD_NOTE,
        ),
    ]


def write_report_key_results_csv(
    path: str | Path,
    rows: Sequence[ReportKeyResult],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REPORT_KEY_RESULTS_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def _format_main_report(metrics: EngineeringReportMetrics) -> str:
    return f"""# Foldable Tip-Hinged Propeller V2 — Engineering Design Report

## 1. Title and Abstract

**Title:** Tip-Hinged Foldable Propeller V2 — Model-Based Engineering Design Study

**Abstract:** This report documents the engineering design and model-based performance evaluation
of a tip-hinged foldable propeller concept for a compact UAV platform. The V2 modeling stack
combines hinge kinematics, moment-based deployment, effective-diameter thrust splitting,
fixed calibration against a 7100 rpm engineering checkpoint, variant screening, and a
motor-coupled post-processing layer. At the interpolated 7100 rpm checkpoint, the calibrated
foldable pretest configuration delivers approximately **{metrics.foldable_pretest_thrust_7100:.2f} N**
versus **{metrics.root_only_20cm_thrust_7100:.2f} N** for the compact 20 cm root-only baseline
(**+{metrics.gain_vs_compact_20cm_root_percent:.1f}%** gain). The same foldable case remains
approximately **{metrics.loss_vs_25cm_reference_percent:.1f}%** below the fixed 25 cm reference
(**{metrics.fixed_25cm_reference_thrust_7100:.2f} N**). All results are simulation outputs and
require CFD and experimental validation before manufacturing decisions.

## 2. Problem Definition

The design problem is to increase aerodynamic thrust beyond a compact stowed-root configuration
while preserving a small mechanical envelope suitable for tube-launched or backpack-stowed UAVs.
A fixed 25 cm propeller provides a known performance upper bound but conflicts with stowage
constraints. A foldable tip-hinged architecture trades some peak thrust for deployable span.

## 3. Design Objective

Primary objectives:

1. Deploy from a ~20 cm effective root to near 25 cm aerodynamic diameter at operating rpm.
2. Achieve calibrated pretest thrust near **70%** of the same-diameter reference at 7100 rpm.
3. Maintain a traceable modeling path from geometry → deployment → thrust → motor checkpoint.
4. Keep reporting gains referenced to the **compact 20 cm root**, not variant-internal segments.

## 4. Foldable Tip-Hinged Propeller Concept

The V02 configuration (`TIP_HINGED_250_V02`) uses a parallel-stow tip segment hinged at the root
blade boundary. Two blades are modeled; visualization uses a single-arm concept frame for
diagnostics. Open diameter is 250 mm; stowed envelope target is 140 mm. Deployment is driven
by centrifugal and aerodynamic hinge moments rather than a prescribed schedule alone.

## 5. Modeling Architecture

The V2 stack is layered and additive:

| Layer | Role |
|-------|------|
| Prescribed-RPM physics | Deployment equilibrium and thrust at fixed rpm |
| Calibrated thrust split | Fixed pretest/target factors from latch reference |
| Design decision matrix | Variant and case ranking |
| Motor-coupled post-process | PyThrust equilibrium + interpolated 7100 rpm checkpoint |

Core PyThrust propulsion solvers are not modified. Foldable modules consume propeller database
entries (APC reference) and battery/motor parameters from JSON configuration.

## 6. Kinematic Model

Hinge angle `theta` is bounded between stowed and open limits. Deployment progress is derived
from geometry helpers linking theta to geometric effective diameter. Kinematics mode is
**moment_based** with optional bias, stiffness scaling, and latch diagnostics for open-stop
behavior.

## 7. Moment-Based Deployment Model

Hinge equilibrium combines:

- Centrifugal moment (geometric radial model in V02)
- Aerodynamic hinge moment (scaled from quasi-steady load)
- Spring, damping, friction, and stop contact

Cases such as `latch_theta0` represent latched full deployment; bias/stiffness sweeps explore
partial deployment without a latch.

## 8. Effective Diameter and Thrust Model

Thrust is computed from reference-scaled propeller coefficients applied to:

- Root segment diameter (compact baseline)
- Aerodynamic effective diameter `D_aero` at deployment state

Ideal thrust uses full tip contribution; calibrated pretest applies a **fixed** factor derived
from the latch reference case (`pretest_70_percent_fixed`).

## 9. Calibration Logic

Calibration anchors to the latch open-stop reference at 7100 rpm:

- **Pretest target:** 70% of 25 cm reference thrust (engineering checkpoint fraction)
- **Project target:** 85% for forward-looking design margin
- Applied factors are **fixed** across cases; required per-case factors remain diagnostic-only

Reporting must use `gain_vs_compact_root_20cm_percent`, not variant-internal root segment gains
(e.g. RT65_35 internal ~292% is diagnostic only).

## 10. Variant Decision Layer

Variants (RT75_25, RT65_35, V02 baseline) are screened via deployment sweeps, performance
summaries, and candidate ranking CSVs. Motor-coupled evaluation confirms that **RT65_35 +
bias10_k0.25_s5** matches latch performance at 7100 rpm while **V02 + bias5_k0.25_s5** is the
best no-latch V02 candidate (~6.33 N pretest).

## 11. Motor-Coupled 7100 rpm Checkpoint

Motor scalars are interpolated at **7100 rpm** from a discrete throttle sweep:

| Quantity | Value |
|----------|-------|
| Interpolated throttle | {metrics.interpolated_throttle_7100:.3f} |
| Current | {metrics.motor_current_7100:.1f} A |
| Power | {metrics.motor_power_7100:.0f} W |
| Foldable pretest thrust | {metrics.foldable_pretest_thrust_7100:.2f} N |
| Compact root thrust | {metrics.root_only_20cm_thrust_7100:.2f} N |
| Fixed 25 cm reference | {metrics.fixed_25cm_reference_thrust_7100:.2f} N |
| Gain vs compact root | +{metrics.gain_vs_compact_20cm_root_percent:.1f}% |
| Loss vs 25 cm reference | {metrics.loss_vs_25cm_reference_percent:.1f}% |
| Motor coupling level | `{metrics.motor_coupling_level}` |

Aero torque (foldable proxy): root 20 cm = **{metrics.aero_torque_root_20cm:.4f} Nm**;
deployed foldable ≈ **{metrics.aero_torque_foldable:.4f} Nm**.
Motor torque margin at foldable load ≈ **{metrics.motor_torque_margin_foldable_nm:.4f} Nm**
({metrics.motor_torque_margin_foldable_percent:.1f}%).

## 12. Engineering Discussion

The foldable concept closes roughly **70%** of the gap between compact root and full reference
 thrust at the checkpoint rpm. Compactness is preserved through parallel tip stow. The motor can
 reach 7100 rpm within the swept throttle range (~0.77 interpolated).

The design is attractive when stowage envelope dominates: foldable pretest thrust is nearly
double the compact root baseline while remaining ~30% below the non-foldable 25 cm reference.
Partial-deployment candidates offer tuning knobs (bias angle, stiffness) without changing core
PyThrust physics.

## 13. Limitations

See `model_assumptions_and_limits.md` for the full list. Critical items:

- Motor coupling is **reference_load_postprocess** — foldable `D_aero` load is not fed back
  into the PyThrust equilibrium solver.
- Calibrated thrust uses fixed proxy factors, not blade-resolved CFD.
- No experimental thrust stand validation is included in this repository state.
- Structural stress, fatigue, balancing, and manufacturing tolerance are out of scope.

## 14. CFD/BEM Future Work

Recommended next steps:

1. BEM or CFD validation of tip segment contribution vs effective-diameter proxy.
2. Coupled motor–propeller solver with foldable `D_aero` torque feedback.
3. Wind-tunnel or thrust-stand comparison at 6547 rpm (operating) and 7100 rpm (checkpoint).
4. Hinge/latch mechanism FEA for open-stop and stow retention.

## 15. Conclusion

The V2 foldable tip-hinged propeller model demonstrates a credible compactness–performance
trade-off at the 7100 rpm engineering checkpoint. Calibrated pretest thrust of
**~{metrics.foldable_pretest_thrust_7100:.2f} N** vs **~{metrics.root_only_20cm_thrust_7100:.2f} N**
compact root confirms meaningful deployment benefit; remaining gap to **~{metrics.fixed_25cm_reference_thrust_7100:.2f} N**
reference is expected and structurally acceptable for the stowage constraint. Results are
model-based and must be validated before final design sign-off.

---

*Generated from `outputs/foldable/dynamics/physics/motor_coupled_7100rpm_interpolated_v2.csv`.
See `report_key_results.csv` and `report_conclusion_tr.md` for summary tables.*
"""


def _format_assumptions_and_limits() -> str:
    return f"""# Model Assumptions and Limits — Foldable V2

## Motor and propulsion coupling

- **Coupling level:** `{MOTOR_COUPLING_LEVEL}`
- RPM, current, and power come from PyThrust equilibrium on the **reference propeller load**.
- Foldable `D_aero` aerodynamic torque is **post-processed** and not yet fed back into the
  solver (`fully_coupled_solver` not implemented).

## Thrust and calibration

- Thrust uses reference-scaled propeller database coefficients (APC entry), not blade-resolved
  CFD or BEM.
- Calibrated pretest thrust applies a **fixed** factor from the latch reference case; it is a
  engineering proxy, not measured tip efficiency.
- 0.70 / 0.85 fractions are **targets** against the 25 cm reference, not guaranteed
  experimental outcomes.

## Aerodynamics and deployment

- Quasi-steady hover (J=0) aerodynamics with effective diameter scaling.
- Tip aero effectiveness modulates folded vs open contribution in dynamic V1; V2 prescribed-rpm
  path uses deployment-state `D_aero`.
- No CFD, no BEM, no wake interaction between blades beyond database scaling.

## Validation gaps

- **No experimental validation** (thrust stand, RPM telemetry, deployment video metrology).
- **No structural stress analysis** on hinge, latch, or root attachment.
- **No fatigue or balancing analysis** for repeated deploy/stow cycles.
- **No manufacturing tolerance** or blade twist defect model.

## Hinge and latch assumptions

- Hinge stiffness, friction, damping, and stop contact are parameterized constants.
- Open latch (`latch_theta0`) represents ideal full deployment to mechanical stop.
- Partial deployment cases depend on bias angle and stiffness multipliers — mechanism-specific
  latch timing is not modeled in detail.
- Single-arm concept frame is used for diagnostics; full two-blade rotor symmetry is assumed
  for thrust doubling implicitly via configuration.

## Reporting cautions

- Use **gain_vs_compact_20cm_root** for external reporting.
- Do **not** use RT65_35 internal variant-root gain (~292%) as the main project metric.
- Separate checkpoint (7100 rpm, 9.10 N reference) from operating (~6547 rpm) references when
  comparing ratios.
"""


def _format_conclusion_tr(metrics: EngineeringReportMetrics) -> str:
    return f"""# Mühendislik Tasarım Raporu — Sonuç Paragrafı

Katlanır uç-mafsallı V2 pervane tasarımı, model tabanlı değerlendirmede kompakt **20 cm kök
bazına** göre anlamlı bir itki artışı sağlamaktadır. 7100 rpm mühendislik kontrol noktasında
kalibrasyonlu ön-test foldable itki yaklaşık **{metrics.foldable_pretest_thrust_7100:.2f} N**,
kompakt kök-only referans **{metrics.root_only_20cm_thrust_7100:.2f} N** seviyesindedir; bu da
yaklaşık **%{metrics.gain_vs_compact_20cm_root_percent:.1f}** kazanç anlamına gelir. Aynı
çalışma noktasında sabit **25 cm** referans pervane (**{metrics.fixed_25cm_reference_thrust_7100:.2f} N**)
karşısında foldable çözüm yaklaşık **%{metrics.loss_vs_25cm_reference_percent:.1f}** daha düşük
kalmaktadır; bu durum katlanabilirlik–performans dengesinin beklenen bir sonucudur.

Tasarım, taşınabilirlik ve depolama zarfı kısıtlı platformlar için avantajlıdır: tam açık
referans kadar itki üretemese de, katlanmış kök konfigürasyonuna kıyasla görev itki seviyesine
yaklaşmaktadır. Motor tarafında 7100 rpm, throttle interpolasyonu ile erişilebilir görünmekte
ancak foldable aerodinamik yük henüz PyThrust denge çözücüsüne geri beslenmemektedir
(`reference_load_postprocess`).

**Sonuç olarak:** mevcut bulgular tasarımın fizibilitesini destekler; ancak bunlar deneysel
doğrulama, CFD/BEM analizi ve mekanik latch/menteşe dayanım çalışmaları tamamlanmadan imalat
kararı verilmemelidir.
"""


def _format_figure_index(project_root: Path) -> str:
    lines = [
        "# Figure Index — Foldable V2 Engineering Design Report",
        "",
        "Paths are relative to the repository root.",
        "",
        "| File | Purpose | Report-ready | Caution |",
        "|------|---------|--------------|---------|",
    ]
    for rel_path, purpose, report_ready, caution in FIGURE_CATALOG:
        exists = (project_root / rel_path).is_file()
        status = "yes" if report_ready else "no"
        note = caution if caution else "—"
        if not exists:
            note = f"File not found on disk. {note}"
        lines.append(f"| `{rel_path}` | {purpose} | {status} | {note} |")

    lines.extend(
        [
            "",
            "## Report-ready summary",
            "",
            "Preferred V2 physics figures under "
            "`outputs/foldable/dynamics/physics/figures/` (constant_7100_* and diag_bias10_*).",
            "",
            "## Use with caution",
            "",
            "- Design-variant sweep figures under `outputs/foldable/figures/` (pre-motor-coupled).",
            "- Dynamic spin-up figures under `outputs/foldable/dynamics/figures/` (V1 transient).",
            "- Frame sequences under `outputs/foldable/dynamics/frames/` (animation stills only).",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_foldable_v2_engineering_design_report(
    project_root: str | Path,
    *,
    interpolated_csv_relative: str = (
        "outputs/foldable/dynamics/physics/motor_coupled_7100rpm_interpolated_v2.csv"
    ),
    report_dir_relative: str = f"reports/{REPORT_DIR_NAME}",
    report_dir: Path | None = None,
) -> list[Path]:
    """Generate all engineering design report artifacts."""
    root = Path(project_root)
    out_dir = report_dir if report_dir is not None else root / report_dir_relative
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = load_engineering_report_metrics(root / interpolated_csv_relative)
    key_results = build_report_key_results(metrics)

    written: list[Path] = []

    main_path = out_dir / MAIN_REPORT_NAME
    main_path.write_text(_format_main_report(metrics), encoding="utf-8")
    written.append(main_path)

    key_csv_path = out_dir / KEY_RESULTS_NAME
    write_report_key_results_csv(key_csv_path, key_results)
    written.append(key_csv_path)

    fig_index_path = out_dir / FIGURE_INDEX_NAME
    fig_index_path.write_text(_format_figure_index(root), encoding="utf-8")
    written.append(fig_index_path)

    assumptions_path = out_dir / ASSUMPTIONS_NAME
    assumptions_path.write_text(_format_assumptions_and_limits(), encoding="utf-8")
    written.append(assumptions_path)

    conclusion_path = out_dir / CONCLUSION_TR_NAME
    conclusion_path.write_text(_format_conclusion_tr(metrics), encoding="utf-8")
    written.append(conclusion_path)

    return written
