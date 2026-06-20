# V2 Hinge Opening Moment Geometry Audit

**Date:** 2026-06-20  
**Scope:** Prescribed-RPM V2 physics path (`hinge_moments.py`, `hinge_moment_geometry.py`)

## Current (legacy) formula — `progress_lever`

```
progress = (theta_deg - theta_min_deg) / (theta_max_deg - theta_min_deg)
lever    = L * (1 - progress)
M_cent   = m * omega^2 * r_cg * lever
```

Where:

| Symbol | Source | Value (V02) |
|--------|--------|-------------|
| `L` | `tip_segment_length_m` | 0.025 m |
| `r_cg` | `tip_segment_cg_from_hinge_m` | 0.0125 m |
| `m` | `tip_segment_mass_kg` | 0.002 kg |
| `theta_min` | folded parallel stow | -180 deg |
| `theta_max` | fully open | 0 deg |

### Lever arm definition

The lever is **not** derived from blade orientation in the rotation plane. It is a normalized
**deployment progress** scalar mapped linearly to `[0, L]`:

- Folded (`theta = -180`): `progress = 0` → `lever = L` (maximum)
- Open (`theta = 0`): `progress = 1` → `lever = 0` (zero)

`hinge_radius_m` is **not used** in this model.

## Why equilibrium occurs around -150 deg

At 7100 rpm, quasi-static balance `M_cent = M_stiff` with `M_stiff = k * (theta - theta_min)` gives:

| theta | lever | M_cent (approx) | M_stiff (approx) |
|-------|-------|-----------------|------------------|
| -180 | L | 0.346 N·m | 0 |
| -150 | 0.83 L | 0.288 N·m | 0.288 N·m |
| 0 | 0 | 0 | 1.73 N·m |

The model **by construction** drives `M_cent → 0` as the blade approaches open. With
`k = 0.55 N·m/rad`, centrifugal moment balances spring stiffness near **-150 deg** (~17%
deployment progress). This is a **model equilibrium**, not full physical deployment.

## Why theta = 0 (open) is not reached

Two coupled reasons:

1. **Moment balance:** At `theta = 0`, `lever = 0` → `M_cent = 0`, while `M_stiff > 0`.
   Net moment closes the blade unless an external opening torque or stop holds it open.
2. **Geometry consistency:** Parallel-stow radial extension at -150 deg is only
   `L * (cos(-150)+1)/2 ≈ 0.0017 m` (~7% of full extension), so the tip remains
   effectively stowed even though the progress lever treats the blade as 17% open.

There is no path to `theta = 0` under pure moment balance with this lever law.

## Why tip thrust remains ~0 N

Tip thrust scales with `tip_radial_extension_m` and lagged aero effectiveness.
At `theta ≈ -150 deg`:

```
extension = L * (cos(-150) + 1) / 2 ≈ 0.0017 m
D_geo     = 2 * (hinge_position + extension) ≈ 0.203 m
```

The progress-lever model reports partial deployment, but the **geometric extension**
(stow model) remains near folded → tip annulus contributes ~0 N thrust.

## New explicit model — `geometric_radial`

Derived from hinge at radius `R_h` and tip CG offset `r_cg` at blade angle `phi`:

```
phi   = theta_deg + deployment_bias_angle_deg
M_cent = scale * m * omega^2 * R_h * r_cg * sin(-phi)
```

| Term | Meaning |
|------|---------|
| `R_h` | `hinge_radius_m` (fallback: `hinge_position_m`) |
| `r_cg` | `tip_segment_cg_from_hinge_m` |
| `sin(-phi)` | Perpendicular moment arm / `R_h` from radial centrifugal force |
| `deployment_bias_angle_deg` | **Explicit** imperfect-stow offset (default 0) |
| `initial_stow_offset_deg` | **Explicit** simulation start angle offset from `theta_min` |
| `cent_moment_geometry_scale` | Diagnostic scale on geometry term (default 1) |

### Physical interpretation

| State | phi | sin(-phi) | M_cent | Hold mechanism |
|-------|-----|-----------|--------|----------------|
| Parallel stow (-180) | -π | ≈ 0 | ≈ 0 | No deterministic opening from perfect parallel fold |
| Mid sweep (-90) | -π/2 | 1 | maximum | Moment balance possible |
| Open (0) | 0 | 0 | 0 | **Mechanical stop/latch** (`open_stop`), not M_cent |

Open state is **not** sustained by centrifugal moment — it requires a hard stop at
`theta_max` or a latch. The V2 physics path reports `hinge_state = open_stop` when
`theta` rests at the open limit.

### Deployment start offset (explicit assumption)

A perfectly parallel folded blade has `sin(-phi) ≈ 0` → no opening moment. Real blades
may rest slightly off-parallel. This is modeled openly via:

- `deployment_bias_angle_deg` — shifts phi in the moment formula
- `initial_stow_offset_deg` — shifts starting theta (e.g. -170 deg instead of -180 deg)

Both default to **0**; non-zero values must be documented as explicit assumptions.

## Hinge state labels (V2 physics path)

| State | Condition |
|-------|-----------|
| `folded` | At `theta_min`, at rest, opening ≤ resisting |
| `opening` | Moving or not at rest equilibrium |
| `equilibrium_partial` | At rest between limits, moment balance |
| `open_stop` | At `theta_max`, held by mechanical stop/latch |

Legacy motor spin-up path retains `folded` / `opening` / `fully_open` / `saturated_open`.

## Diagnostic variants

See `outputs/foldable/dynamics/physics/hinge_moment_geometry_diagnostic.csv`:

1. `progress_lever_baseline` — legacy model
2. `geometric_radial_no_offset` — explicit geometry, zero bias
3. `geometric_radial_bias_10deg` — imperfect stow bias
4. `geometric_radial_reduced_stiffness` — k × 0.25
5. `geometric_radial_scale_2x` — geometry scale × 2
