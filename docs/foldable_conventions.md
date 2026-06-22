# Katlanabilir Pervane Birim ve Açı Konvansiyonları

Bu belge, `pythrust/foldable/` modülünde kullanılan fiziksel büyüklük ve açı
konvansiyonlarını tanımlar. katlanır pervane modülü kapsamında üretilen tüm
sayısal çıktılar bu standarda uyar.

## Birimler

| Büyüklük | Birim | Sembol |
|---|---|---|
| Uzunluk (çap, kanat uzunluğu, mafsal konumu) | metre | m |
| Kütle (uç segment) | kilogram | kg |
| İtki | newton | N |
| Tork | newton-metre | N·m |
| Güç | watt | W |
| Akım | amper | A |
| Voltaj | volt | V |
| Devir hızı | devir/dakika | RPM |
| Hava yoğunluğu | kilogram/metreküp | kg/m³ |
| Açı (kullanıcı girdisi ve CSV çıktısı) | derece | deg |
| Açı (iç hesaplama) | radyan | rad |

Tüm uzunluklar **metre**, kütle **kg**, thrust **N**, güç **W** cinsinden
ifade edilir. RPM birimi **rev/min** (devir/dakika) olarak kullanılır.

## Açı Konvansiyonu

- Kullanıcı girdileri ve CSV çıktıları **derece** (`theta_deg`) cinsindendir.
- Trigonometrik iç hesaplamalarda **radyan** (`theta_rad`) kullanılır.
- Dönüşüm: `theta_rad = theta_deg * π / 180`

### İşaret ve fiziksel anlam

| `theta_deg` | Durum | Açıklama |
|---|---|---|
| `0` | Tam açık | Uç segment radyal konumda; efektif çap maksimum |
| Negatif değerler | Katlanmış | Uç segment geriye/yanlara eğik; efektif çap azalır |
| `theta_min_deg` | Tam katlı | Konfigürasyonda tanımlı alt sınır (ör. −45°) |

`theta_deg = 0` tam açık durumu temsil eder. Negatif `theta_deg` değerleri
katlanmış (kapalı veya kısmen kapalı) durumu temsil eder.

## Efektif Çap

`effective_diameter_m`, uç segment açılma açısına (`theta_deg`) bağlı olarak
hesaplanan efektif pervane çapıdır (metre).

Geometrik yaklaşım (V1):

```
R_eff = hinge_position_m + tip_segment_length_m * cos(theta_rad)
effective_diameter_m = 2 * R_eff
```

Tam açık durumda (`theta_deg = 0`):

```
effective_diameter_m = diameter_open_m
```

Örnek: `diameter_open_m = 0.25 m` için tam açıkta efektif çap 0.25 m olmalıdır.

`effective_diameter_m`, uçuş başlangıcında pervane açısına bağlı **aerodinamik/radyal
efektif çap**tır. İtki hesaplamasında kullanılır; katlanmış depolama zarfı ile
aynı büyüklük değildir.

## Katlanmış Depolama Zarfı

`stowed_envelope_diameter_m`, tekerlek/şasi üzerinde katlanmış pervanenin
hedeflenen **depolama zarf çapı**dır (metre). tasarım önerisinde tam açık
hedef 0.25 m, katlanmış zarf hedefi 0.14 m olarak tanımlanmıştır.

| Alan | Anlam | İtki modelinde kullanım |
|---|---|---|
| `diameter_open_m` | Tam açık geometrik çap hedefi | Evet (referans geometri) |
| `effective_diameter_m` | Anlık aerodinamik/radyal efektif çap | Evet |
| `stowed_envelope_diameter_m` | Katlanmış depolama zarf hedefi | Hayır (yalnızca dokümantasyon ve görselleştirme) |

Ground mode thrust analiz edilmez; `stowed_envelope_diameter_m` yalnızca tasarım
ve depolama kısıtı olarak raporlanır.

## Mafsal Kinematiği

`kinematics.kinematics_mode` ile seçilir:

| Mod | Açıklama |
|---|---|
| `rpm_only` | RPM eşiklerine bağlı doğrusal doygunluk; tüm varyantlarda aynı θ(RPM) |
| `moment_based` | Geometriye bağlı moment dengesi; varyantlar farklı θ üretebilir |

### Moment-based hinge kinematics (V2)

Basit denge modeli (CFD/BEMT/deneysel doğrulama henüz yok):

```
omega = rpm * 2π / 60
M_open = m_tip * omega² * r_cg * lever_arm
M_resist(theta) = k_hinge * (theta_rad - theta_min_rad) + M_friction
```

| Parametre | Config alanı |
|---|---|
| `m_tip` | `geometry.tip_segment_mass_kg` |
| `r_cg` | `geometry.tip_segment_cg_from_hinge_m` (varsayılan: `tip_segment_length_m / 2`) |
| `lever_arm` | `tip_segment_length_m` (V1 varsayımı) |
| `k_hinge` | `hinge.hinge_stiffness_nm_per_rad` |
| `M_friction` | `hinge.hinge_friction_nm` |
| `hinge_radius_m` | `hinge.hinge_radius_m` — metadata only in V1 |

**Model note:** V1 moment model: hinge_radius_m is stored but not used in opening
moment calculation.

``moment_margin_nm = M_open - M_resist`` yorumu:

| `hinge_state` | `moment_margin_nm` |
|---|---|
| `opening` | Denge: yaklaşık 0 |
| `folded` | `M_open <= M_resist`; yaklaşık 0 |
| `saturated_open` | Pozitif: fazla `M_open` mekanik durakta karşılanır |
| `fully_open` | Denge `theta_max`'ta, durak yok |

Karar skoru ``active_window_diameter_growth_score`` (tercih edilen etiket; CSV'de
``deployment_score`` geriye dönük uyumluluk için korunur):

**Model note:** active_window_diameter_growth_score measures observed diameter
growth over sampled throttle values, not total stowed-to-open geometric deployment.

Ham değer: örneklenen throttle penceresinde ``(D_max - D_min) / D_max``.

Çözüm: `M_open ≤ M_friction` veya `rpm ≤ 0` → `theta_min_deg`; aksi halde
`theta_rad = theta_min_rad + (M_open - M_friction) / k_hinge`, sonra
`[theta_min_deg, theta_max_deg]` aralığına kısıtlanır.

`rpm_only` modu geriye dönük uyumluluk için korunur; `rpm_threshold` ve
`rpm_full_open` yalnızca bu modda kullanılır.

## 2D Engineering Visualization (V1)

2D radial schematic / effective-diameter visualization (hub → root → hinge → tip)
driven by existing CSV outputs. No physics recomputation.

**Diameter overlays:**

- `diameter_open_m` — dotted open-target circle
- `effective_diameter_m` — dashed D_eff circle (from sweep/moment CSV)
- `stowed_envelope_diameter_m` — optional dotted reference circle from config
  (proposal storage envelope; not used in thrust calculation)

**Coordinate convention:** hub at `(0, 0)`; hinge at `(hinge_position_m, 0)`;
tip at `(hinge_position_m + L·cosθ, L·sinθ)` with `L = tip_segment_length_m`.

**Inputs:**

- `outputs/foldable/design_variant_sweep.csv` — thrust, compactness
- `outputs/foldable/moment_kinematics_validation.csv` — moments, hinge_state
- `outputs/foldable/variant_physical_parameters.csv` — segment lengths

**Outputs:** `outputs/foldable/visuals/` (radial + concept figures,
`foldable_2d_visuals_report.md`).

Generate via `examples/run_foldable_visuals.py` after sweep and moment validation
CSVs exist.

## Concept / Deployment Schematic Visualization (V2)

Presentation/mechanical explanation visuals with **folded-start interpretation**.
Uses `PropellerVisualState` plus visualization-only mapping; no physics recomputation.

**Angle mapping (visualization only):**

- Model `theta_deg`: 0° = radial open, negative = folded (analysis frame)
- `deployment_progress_01 = (theta_deg - theta_min_deg) / (0 - theta_min_deg)`
- `display_hinge_angle_deg`: 180° at progress=0 (secondary parallel to main, toward hub),
  0° at progress=1 (secondary radial open)

Concept secondary blade is drawn from `display_hinge_angle_deg`, **not** raw `theta_deg`.

**Component mapping:**

- Main blade / Ana Kanat — hub to hinge (root segment)
- Secondary blade / İkincil Kanat — hinge to tip (`display_hinge_angle_deg`)
- Hinge / Eklem — visible joint marker
- Motor connection / Motor Bağlantısı — stylized hub hole (illustrative only)

**Concept outputs:**

- `concept_static_overview.png` — folded-start bilingual labeled overview
- `concept_state_*.png` — single-state schematic with compact info box
- `concept_throttle_sweep_*.png` — pseudo-time deployment sweep panel (t=0 folded → open)
- `concept_variant_compare_thr_*.png` — concept deployment-style RT65_35 … RT85_15
  comparison at fixed throttle; compact labels: variant, θ, hinge_state, D_eff
- `concept_deployment_sequence_*.png` — pseudo-time deployment sequence (folded → open)
- `frames/concept_<variant_id>/` — per-frame PNGs (`frame_000.png`, …), `manifest.json`,
  and optional `frames_metadata.csv` for animation
- `concept/frames/<variant_id>/deployment/` — legacy uniform-progress frame export

**Pseudo-time (first-step concept deployment):** panel index maps to
`t = index / (N-1) × DEPLOYMENT_SEQUENCE_DURATION_S` (default 2.0 s). At t=0 the secondary
blade uses folded display angle (180°); later frames interpolate toward open (0°). This is
visualization-only — not a dynamic rigid-body simulation. Sweep CSV rows provide model
context per throttle; concept opening geometry follows panel progress index.

**Frame manifest / CSV fields:** `frame_index`, `time_s`, `deployment_progress_01`,
`display_hinge_angle_deg`, `source_throttle`, `source_theta_deg`, `source_state_id`

**Radial vs concept:**

| Aspect | Radial / effective-diameter (analysis) | Concept deployment (presentation) |
|---|---|---|
| Purpose | D_eff analysis and validation | Folding/deployment explanation |
| Secondary angle | Model `theta_deg` | `display_hinge_angle_deg` |
| Start visual | Model angle at each state | Folded parallel baseline in static overview |

**Limitations:** not CAD, not CFD, not true airfoil geometry; illustrative blade
width and motor connection in V1.

## Dynamic spin-up (V1 skeleton)

Time-dependent ODE layer under `pythrust/foldable/dynamics/` — additive to the
static/quasi-static foldable model.

**Outputs:**

- `outputs/foldable/dynamics/dynamic_spinup_RT75_25_step.csv` — step throttle time history
- `outputs/foldable/dynamics/dynamic_spinup_RT75_25_ramp.csv` — linear ramp startup
  (`ramp_time_s=0.5`)
- `outputs/foldable/dynamics/dynamic_spinup_RT75_25.csv` — legacy alias of step CSV
- `outputs/foldable/dynamics/dynamic_spinup_summary_RT75_25_step.csv` — checkpoint
  checkpoint summary (step profile)
- `outputs/foldable/dynamics/dynamic_spinup_summary_RT75_25_ramp.csv` — checkpoint
  checkpoint summary (ramp profile)
- `outputs/foldable/dynamics/dynamic_spinup_summary_RT75_25.csv` — legacy alias of
  step summary
- `outputs/foldable/dynamics/figures/spinup_RT75_25_step.png` — 4-panel step summary
  (RPM, θ, thrust, D_eff vs time) with 7100 rpm checkpoint annotations
- `outputs/foldable/dynamics/figures/spinup_RT75_25_ramp.png` — 4-panel ramp summary
- `outputs/foldable/dynamics/figures/spinup_RT75_25_step_report.png` — report-clean
  step figure (checkpoint box in reserved margin)
- `outputs/foldable/dynamics/figures/spinup_RT75_25_ramp_report.png` — **preferred
  report figure** for startup visualization (linear ramp, `ramp_time_s=0.5`)
- `outputs/foldable/dynamics/figures/spinup_RT75_25.png` — legacy alias of step figure
- `outputs/foldable/dynamics/frames/RT75_25/` — rotating **single-arm concept frame**
  PNGs (step profile) + `manifest.json`
- `outputs/foldable/dynamics/frames/RT75_25_ramp/` — ramp-profile frames with the
  same single-arm concept visualization

**Optional config fields:**

- `geometry.rotor_inertia_kgm2` — override estimated rotor inertia
- `hinge.hinge_damping_nm_s_per_rad` — viscous damping (V2 physics path; 0 in V1 motor spin-up)

## Propeller-first physics (V2)

Prescribed-RPM validation path under `pythrust/foldable/dynamics/` — **no motor module**.
Use config `TIP_HINGED_250_V02.json` with parallel-stow geometry.

**Angle convention (V02):**

- `theta_deg = 0` — fully open (tip radial)
- `theta_deg = -180` — parallel stow (tip aligned with root toward hub)
- V01 `theta_min = -45°` retained for legacy motor spin-up (`legacy_cos` stow model)

**Geometry outputs:**

- `tip_radial_extension_m` — radial tip contribution beyond hinge
- `geometric_effective_diameter_m` — `2 * (hinge_position + extension)`
- `aerodynamic_effective_diameter_m` — root/tip blend with lagged tip effectiveness

**Simulation modes:**

| Mode | Entry point | RPM source | Hinge |
|------|-------------|------------|-------|
| Motor spin-up (legacy) | `run_spinup_simulation` | Motor ODE | Quasi-static |
| Prescribed RPM (V2) | `run_prescribed_rpm_physics` | `PrescribedRpmConfig` | Second-order ODE |

**Physics debug outputs** (`outputs/foldable/dynamics/physics/`):

- CSV: `prescribed_rpm_7100_constant.csv`, `prescribed_rpm_ramp.csv`
- Figures: hinge kinematics, moment components, split thrust, D_geo vs D_aero, phase portrait
- Example: `examples/run_prescribed_rpm_physics.py`

**Hinge ODE:** `J * theta_ddot = M_cent + M_aero - M_stiff - M_damp - M_fric - M_stop`

**Thrust split:** `thrust_root_n` (active from start) + `thrust_tip_n` (angle/lagged eff)

**Dynamic V1 notes:**

- `D_eff` = aerodynamic effective diameter during deployment; **not** the 0.14 m
  `stowed_envelope_diameter_m` storage target.
- `aero_effectiveness` scales thrust/torque by deployment progress (folded overlap
  approximation); V1 approximation only, not a full folded-blade aero model.
- Throttle `step` profile is an ideal command (instant full throttle after t=0).
- Throttle `linear_ramp` profile is more realistic for startup visualization
  (default `ramp_time_s=0.5` s). Use `spinup_RT75_25_ramp_report.png` in written
  reports; keep step figures for ideal-command upper-bound comparison.
- Checkpoint summary CSVs at 7100 rpm (per profile); legacy step alias kept.
- Legacy spin-up figures keep inline checkpoint annotations; `*_report.png` figures
  reserve a right margin so subplot titles stay readable.
- Dynamic frame export uses a **single-arm concept frame**: root + hinged tip segment
  only; it does **not** yet represent a full two-blade rotor or CAD geometry. Optional
  text overlay shows θ, hinge state, D_eff, thrust, and input profile label.
- `ideal_geometry_ratio_at_7100_rpm` = simulated thrust / reference open propeller
  thrust at 7100 rpm when the model is fully deployed; **not** experimental
  performance (assumes no profile/hinge/manufacturing loss once open).
- `current_pretest_ratio` (0.70) is the **pretest reference** vs the
  same-diameter standard propeller; not an automatic V1 model result.
- `project_target_ratio` (0.85) is the **project target**; future
  BEM/CFD/experiment calibration required.
- `current_calibrated_thrust_at_7100_rpm` and `target_thrust_at_7100_rpm` scale
  the reference thrust by those calibration fractions for proposal alignment.

**Calibration reference hooks** (`dynamics/calibration.py`): 25 cm open diameter,
14 cm stowed envelope, 7100 rpm pretest, 70% pretest / 85% project lift targets
(future BEM/CFD/experiment calibration).

## Çıktı Dosyaları

Sweep ve karşılaştırma tabloları `outputs/foldable/` altında CSV olarak
üretilir. Minimum sweep kolonları:

`rpm`, `theta_deg`, `effective_diameter_m`, `thrust_n`, `model_note`

Genişletilmiş kolonlar (ileride PyThrust entegrasyonu ile):

`voltage_v`, `throttle`, `torque_nm`, `current_a`, `power_w`, `efficiency`

## Model Sürümü

V1 modeli basitleştirilmiş ve kalibre edilebilir bir sayısal yaklaşımdır.
V2 moment-based kinematics geometriye bağlı θ hesabı ekler; thrust modeli hâlâ
`reference_scaled` yaklaşımındadır. CFD, BEMT veya deneysel Ct/Cp verileri
ileride aynı arayüz üzerinden entegre edilebilir.
