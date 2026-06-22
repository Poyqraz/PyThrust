# Foldable Propeller V2 Physics Realism — Design Spec

**Date:** 2026-06-20  
**Status:** Approved for implementation

## Goal

Increase physical realism of the foldable propeller mechanism via a propeller-first prescribed-RPM validation path, independent of the motor module.

## Angle convention (V02)

| Angle | Meaning |
|-------|---------|
| `theta_deg = 0` | Fully open — tip segment radial (+x) |
| `theta_deg = -180` | Parallel stow — tip aligned with root toward hub, zero radial extension |
| V01 `theta_min = -45°` | Legacy compact-fold approximation (motor spin-up path unchanged) |

## Geometry outputs

- **tip_radial_extension_m:** `L * max(0, (cos(θ)+1)/2)` for parallel_fold
- **geometric_effective_diameter_m:** `2 * (hinge_position + tip_radial_extension)`
- **aerodynamic_effective_diameter_m:** root/tip blend with lagged tip effectiveness

## Hinge dynamics

```
J_hinge * theta_ddot = M_cent + M_aero - M_stiff - M_damp - M_fric - M_stop
```

Default for physics path: second-order ODE. Legacy motor spin-up: quasi-static equilibrium.

## Thrust split

- **Root:** active from t=0 at `D_root = 2 * hinge_position`
- **Tip:** scaled by radial extension and lagged aero effectiveness
- **Total:** `thrust_root_n + thrust_tip_n`

## Assumptions (realism)

- Point-mass tip centrifugal model; no blade flex
- M_aero on hinge is a configurable proxy gain
- Ct/Cp from reference prop DB with diameter scaling (semi-empirical)
- Prescribed RPM intentionally decouples rotor acceleration from deployment

## Still simplified / needs calibration

- BEM/blade-element tip/root loading
- Experimental hinge friction, stiffness, inertia
- Folded-blade wake/interference beyond lag filter
- Multi-blade symmetry (visualization remains single-arm concept)
- Motor re-integration after mechanism validation
