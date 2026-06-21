# Figure Index — Foldable V2 Engineering Design Report

Paths are relative to the repository root.

| File | Purpose | Report-ready | Caution |
|------|---------|--------------|---------|
| `outputs/foldable/dynamics/physics/figures/constant_7100_thrust_split.png` | V2 prescribed-RPM thrust split at 7100 rpm checkpoint | yes | Use with note that values are model-based, not measured. |
| `outputs/foldable/dynamics/physics/figures/constant_7100_phase_portrait.png` | Hinge angle vs angular velocity at constant 7100 rpm | yes | Illustrates deployment equilibrium; single reference case. |
| `outputs/foldable/dynamics/physics/figures/constant_7100_diameter_geo_aero.png` | Geometric vs aerodynamic effective diameter at 7100 rpm | yes | Shows D_geo and D_aero separation in V2 model. |
| `outputs/foldable/dynamics/physics/figures/constant_7100_hinge_kinematics.png` | Hinge kinematics time history at 7100 rpm | yes | Prescribed-RPM diagnostic; not motor-coupled transient. |
| `outputs/foldable/dynamics/physics/figures/constant_7100_moments.png` | Hinge moment balance at 7100 rpm | yes | Moment-based deployment model visualization. |
| `outputs/foldable/dynamics/physics/figures/diag_bias10_thrust_split.png` | Deployment diagnostic thrust split (bias10 case) | yes | Candidate geometry; compare with latch reference. |
| `outputs/foldable/dynamics/physics/figures/diag_bias10_phase_portrait.png` | Deployment diagnostic phase portrait (bias10) | yes | Partial deployment state; not full latch open-stop. |
| `outputs/foldable/dynamics/physics/figures/ramp_thrust_split.png` | Spin-up ramp thrust split | no | Dynamic V1 layer; do not mix directly with V2 motor-coupled tables. |
| `outputs/foldable/dynamics/physics/figures/ramp_phase_portrait.png` | Spin-up ramp phase portrait | no | Transient startup; different coupling level than 7100 checkpoint. |
| `outputs/foldable/figures/foldable_thrust_n_vs_throttle_by_variant.png` | Design-variant thrust vs throttle sweep | no | Pre-motor-coupled design sweep; throttle axis not V2 motor equilibrium. |
| `outputs/foldable/figures/effective_diameter_m_vs_throttle_by_variant.png` | Effective diameter vs throttle by variant | no | Design-variant layer; verify variant ID before citing in V2 report. |
| `outputs/foldable/figures/theta_deg_vs_throttle_by_variant.png` | Hinge angle vs throttle by variant | no | Design-variant sweep; moment model version may differ from V02 config. |
| `outputs/foldable/figures/thrust_difference_percent_vs_throttle_by_variant.png` | Thrust difference vs fixed reference propeller | no | Normalized against APC reference; not calibrated pretest split. |
| `outputs/foldable/figures/fig_thrust_difference_normalized_250mm.png` | Normalized thrust loss vs 250 mm reference | no | Summary metric for variant ranking, not final V2 motor checkpoint. |
| `outputs/foldable/figures/flight_startup_scores_by_variant.png` | Variant decision support scores | no | Decision-support only; not experimental validation. |
| `outputs/foldable/dynamics/figures/spinup_RT75_25_step_report.png` | Step-throttle spin-up report figure | no | Ideal step throttle; not interpolated 7100 rpm operating point. |
| `outputs/foldable/dynamics/figures/spinup_RT75_25_ramp_report.png` | Ramp-throttle spin-up report figure | no | Transient model; coupling level differs from reference_load_postprocess. |

## Report-ready summary

Preferred V2 physics figures under `outputs/foldable/dynamics/physics/figures/` (constant_7100_* and diag_bias10_*).

## Use with caution

- Design-variant sweep figures under `outputs/foldable/figures/` (pre-motor-coupled).
- Dynamic spin-up figures under `outputs/foldable/dynamics/figures/` (V1 transient).
- Frame sequences under `outputs/foldable/dynamics/frames/` (animation stills only).
