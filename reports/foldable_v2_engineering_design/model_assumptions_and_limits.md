# Model Assumptions and Limits — Foldable V2

## Motor and propulsion coupling

- **Coupling level:** `reference_load_postprocess`
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
