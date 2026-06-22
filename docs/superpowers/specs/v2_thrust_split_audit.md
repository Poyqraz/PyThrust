# V2 Thrust Split Model Audit

**Date:** 2026-06-20  
**Scope:** `pythrust/foldable/dynamics/split_thrust.py` (V2 prescribed-RPM path)

## Current model — `independent_tip_disk`

```
d_root       = 2 × hinge_position_m
tip_ext      = tip_radial_extension(theta)
d_tip_equiv  = 2 × tip_ext
T_root       = Ct × ρ × n² × d_root⁴
T_tip        = Ct × ρ × n² × d_tip_equiv⁴ × tip_aero_effectiveness
T_total      = T_root + T_tip
```

Each segment is treated as a **separate actuator disk** with its own diameter raised to the fourth power.

### Example at 7100 rpm (V02, θ ≈ -13°, near-deployed)

| Quantity | Value |
|----------|-------|
| d_root | 0.20 m |
| tip_ext | ~0.025 m |
| d_tip_equiv | ~0.05 m |
| T_root | ~3.73 N |
| T_tip | ~0.014 N |
| T_tip / T_total | ~0.4% |

### Why T_tip ≈ 0.014 N

The tip is modelled as a **5 cm diameter propeller**:

```
(0.05 / 0.20)⁴ = 0.25⁴ ≈ 0.0039
T_tip ≈ 0.004 × T_root ≈ 0.015 N
```

This is mathematically consistent with the formula but **physically misleading** for a foldable blade:
the tip segment is an **outer radial extension** of the same rotor, not an independent micro-propeller.

Meanwhile `D_aero` (linear blend of root + tip annulus) reaches ~0.249 m — the model acknowledges
a larger effective rotor, but the thrust split does not use that diameter for the tip increment.

## Three modelling approaches

### a) Independent tip propeller (`independent_tip_disk`) — current default

- Tip thrust from `d_tip_equiv = 2 × extension` as standalone disk
- **Pros:** Simple, conservative, root always active
- **Cons:** Severely underestimates tip fraction when extension is small relative to root; decoupled from `D_aero`

### b) Effective diameter delta (`effective_diameter_delta`) — BEM-lite proxy

```
T_total_aero = Ct × ρ × n² × D_aero⁴ × k_thrust
T_root       = Ct × ρ × n² × D_root⁴ × k_thrust
T_tip_delta  = max(T_total_aero − T_root, 0)
T_total      = T_root + T_tip_delta
```

Treats deployment as increasing the **single rotor's effective diameter**; tip contribution is the
incremental thrust of the larger disk over the root disk.

- **Pros:** Consistent with `D_aero`; tip thrust grows when D_aero grows; at D_aero = D_root, T_tip = 0
- **Cons:** Still actuator-disk / D⁴ scaling; not blade-element; assumes uniform Ct across radii

### c) Annular extension proxy (`annular_extension_proxy`) — BEM-lite proxy

```
r_inner = D_root / 2
r_outer = D_geo / 2
r_open  = diameter_open / 2
f_ann   = (r_outer² − r_inner²) / (r_open² − r_inner²)   clamped [0, 1]
T_tip   = (T(D_open) − T_root) × f_ann × tip_aero_effectiveness
T_total = T_root + T_tip
```

Tip contribution is a **fraction of the full-deployment thrust increment**, weighted by the
deployed annulus area (not a standalone disk).

- **Pros:** Explicit annular geometry; zero tip when folded; full increment at θ = 0 (open)
- **Cons:** Uses `D_geo` not `D_aero`; area ratio is a proxy not circulation distribution

## Why independent model underestimates outer extension

| Concept | Independent tip disk | Annular / delta model |
|---------|---------------------|----------------------|
| Tip geometry | 5 cm propeller | Outer 12.5 mm annulus of 25 cm rotor |
| Scaling | (0.05)⁴ | (0.25⁴ − 0.20⁴) or area-weighted fraction |
| At D_aero = 0.249 m | T_tip still ~0.014 N | T_tip reflects full rotor increment |

The tip segment adds **circulation at outer radii**, increasing total rotor thrust approximately as
`(D_new/D_old)⁴ − 1`, not as an independent `(d_tip/D_root)⁴` propeller.

## Recommended use (pre-BEM)

| Mode | When to use |
|------|-------------|
| `independent_tip_disk` | Legacy comparison, conservative lower bound |
| `effective_diameter_delta` | When `D_aero` is trusted; simplest consistency with aero diameter |
| `annular_extension_proxy` | When geometric annulus fraction is preferred over D_aero blend |
| `calibrated_effective_diameter_delta` | calibrated reporting with `pretest_70_percent_fixed` or `target_85_percent_fixed` |

### Calibrated effective diameter delta

```
T_tip_calibrated = T_tip_ideal_delta × applied_fixed_factor
T_total          = T_root + T_tip_calibrated
```

Two factor concepts:

| Concept | Meaning |
|---------|---------|
| **Required factor (per case)** | `required_tip / T_tip_ideal_delta` for *this* deployment state so total thrust hits exactly 70% or 85% of the 25 cm reference. Diagnostic only — varies with `D_aero`. |
| **Applied fixed factor** | Single factor derived from the reference case (`latch_theta0` by default): `pretest_required_tip / T_tip_ideal_delta_at_reference`. Applied uniformly so partial deployment shows lower achieved ratios. |

Presets:

- `pretest_70_percent_fixed` — applied fixed factor for 70% reference (recommended default)
- `target_85_percent_fixed` — applied fixed factor for 85% target
- `pretest_70_percent`, `target_85_percent` — legacy aliases mapped to the corresponding `_fixed` preset in simulation

Fixed factors at reference (`latch_theta0`, 7100 rpm):

```
applied_pretest_fixed_factor = pretest_required_tip / T_tip_ideal_delta_reference
applied_target_fixed_factor  = target_required_tip / T_tip_ideal_delta_reference
```

Neither proxy mode is final BEM/CFD — all are labelled **BEM-lite / proxy** models.

## Remaining limitations before BEM/CFD

- Single global `Ct` from reference prop DB (no radial circulation distribution)
- No blade twist, chord, or Reynolds variation along span
- No tip/root interference or folded-wake effects
- `tip_aero_lag_tau_s` is first-order; no dynamic stall
- Annular proxy assumes axisymmetric thrust increment (single-arm concept)
