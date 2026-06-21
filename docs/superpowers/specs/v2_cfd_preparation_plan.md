# V2 CFD Preparation Plan

## Status

**This document describes CFD preparation only. No CFD simulation has been performed.**

The PyThrust foldable V2 stack exports geometry, operating-point, and boundary-condition
tables so that external tools (Ansys Fluent, OpenFOAM, or a BEM-lite validator) can be
configured later. All thrust and torque values in the prep CSVs are **model proxies** from
the existing V2 physics and motor-coupled layers.

## What exists today (Level 1)

| Artifact | Path | Purpose |
|----------|------|---------|
| Operating points | `outputs/foldable/cfd_prep/cfd_operating_points_v2.csv` | RPM, θ, D_aero, thrust/torque targets @ 7100 rpm |
| Geometry parameters | `outputs/foldable/cfd_prep/cfd_geometry_parameters_v2.csv` | Segment lengths, hinge, stow envelope, deployment state |
| Case recommendations | `outputs/foldable/cfd_prep/cfd_case_recommendations_v2.csv` | Priority order for external CFD runs |
| Readiness audit | `outputs/foldable/cfd_prep/cfd_readiness_audit_v2.csv` | Pass/fail/not_available checks |
| Boundary notes | `outputs/foldable/cfd_prep/cfd_boundary_condition_notes.md` | Suggested Fluent/OpenFOAM BC setup |

Generate with:

```bash
python3 examples/run_cfd_preparation.py
```

## What is NOT included

- CAD/STL solid models (placeholder status in audit)
- Volume or surface mesh
- CFD solver input decks (Fluent `.cas`, OpenFOAM `constant/`, etc.)
- CFD post-processed thrust/torque
- Experimental validation data

## External workflow (Ansys Fluent / OpenFOAM)

### Step 1 — Import reference cases

Run cases in priority order from `cfd_case_recommendations_v2.csv`:

1. `fixed_25cm_reference` — upper bound (~9.10 N model target)
2. `root_only_20cm` — compact lower bound (~3.73 N)
3. `latch_theta0` — primary foldable candidate (~6.37 N pretest)
4. `RT65_35 + bias10_k0.25_s5` — alternate geometry
5. `V02 + bias5_k0.25_s5` — best no-latch V02 variant

### Step 2 — Geometry

- Use `cfd_geometry_parameters_v2.csv` for parametric reconstruction until CAD is frozen.
- Build multi-body model: hub, root segment, tip segment at `theta_final_deg`.
- Mark STL/CAD availability in a future audit update when mechanical design exists.

### Step 3 — Steady MRF hover (recommended first)

- ρ = 1.225 kg/m³, J = 0, ω = 7100 rpm (742.5 rad/s).
- MRF zone around propeller; compare integrated thrust/torque to operating-point CSV.
- See `cfd_boundary_condition_notes.md` for inlet/outlet and wall assumptions.

### Step 4 — Compare results

| CFD output | Compare to |
|------------|------------|
| Integrated thrust | `T_pretest_n` in operating points CSV |
| Integrated torque | `aero_torque_nm` (foldable proxy) |
| Pressure field | Not available in V2 model — qualitative only |

Do **not** tune CFD to match calibrated pretest factors inside PyThrust. Compare raw CFD
 thrust to both ideal and calibrated model columns separately.

### Step 5 — Optional transient / sliding mesh

Required only if:

- Deployment during spin-up is in scope
- Tip hinge motion must be time-resolved
- Latch contact or unsteady blade loading is critical

## Level 2 — CFD-lite / BEM-lite (future repo work)

Not implemented in this phase. Planned controls:

- Actuator disk with thrust/torque matched to operating-point CSV
- Annular disk split at hinge radius (root vs tip loading)
- Radial section Ct/Cp proxy vs APC database coefficients

## Level 3 — Full CFD (external)

- CAD/STL from mechanical design
- Mesh refinement study on tip segment and hinge gap
- MRF steady runs → sliding mesh transient if Level 2 mismatch exceeds tolerance
- Validation against thrust stand at 6547 rpm (operating) and 7100 rpm (checkpoint)

## Model comparison targets

| Model layer | What CFD should challenge |
|-------------|---------------------------|
| Effective diameter thrust split | Is D_aero blending physically valid? |
| Calibrated pretest 70% factor | Does raw CFD tip contribution match fixed factor? |
| Quasi-steady aero torque | Does integrated CFD torque match foldable_proxy? |
| Motor-coupled checkpoint | Does 7100 rpm operating point remain feasible with CFD loads? |

## Constraints preserved in this phase

- No changes to V2 physics models
- No changes to calibration factors
- No changes to core PyThrust
- No removal of existing outputs
