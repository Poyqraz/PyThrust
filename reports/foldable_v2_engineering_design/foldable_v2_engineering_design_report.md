# Foldable Tip-Hinged Propeller V2 — Engineering Design Report

## 1. Title and Abstract

**Title:** Tip-Hinged Foldable Propeller V2 — Model-Based Engineering Design Study

**Abstract:** This report documents the engineering design and model-based performance evaluation
of a tip-hinged foldable propeller concept for a compact UAV platform. The V2 modeling stack
combines hinge kinematics, moment-based deployment, effective-diameter thrust splitting,
fixed calibration against a 7100 rpm engineering checkpoint, variant screening, and a
motor-coupled post-processing layer. At the interpolated 7100 rpm checkpoint, the calibrated
foldable pretest configuration delivers approximately **6.37 N**
versus **3.73 N** for the compact 20 cm root-only baseline
(**+70.9%** gain). The same foldable case remains
approximately **30.0%** below the fixed 25 cm reference
(**9.10 N**). All results are simulation outputs and
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
| Interpolated throttle | 0.768 |
| Current | 17.0 A |
| Power | 150 W |
| Foldable pretest thrust | 6.37 N |
| Compact root thrust | 3.73 N |
| Fixed 25 cm reference | 9.10 N |
| Gain vs compact root | +70.9% |
| Loss vs 25 cm reference | 30.0% |
| Motor coupling level | `reference_load_postprocess` |

Aero torque (foldable proxy): root 20 cm = **0.0462 Nm**;
deployed foldable ≈ **0.1411 Nm**.
Motor torque margin at foldable load ≈ **0.0129 Nm**
(8.4%).

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
**~6.37 N** vs **~3.73 N**
compact root confirms meaningful deployment benefit; remaining gap to **~9.10 N**
reference is expected and structurally acceptable for the stowage constraint. Results are
model-based and must be validated before final design sign-off.

---

*Generated from `outputs/foldable/dynamics/physics/motor_coupled_7100rpm_interpolated_v2.csv`.
See `report_key_results.csv` and `report_conclusion_tr.md` for summary tables.*
