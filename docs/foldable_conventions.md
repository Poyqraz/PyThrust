# Katlanabilir Pervane Birim ve Açı Konvansiyonları

Bu belge, `pythrust/foldable/` modülünde kullanılan fiziksel büyüklük ve açı
konvansiyonlarını tanımlar. TÜBİTAK 2209-B projesi kapsamında üretilen tüm
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

## Katlanmış Depolama Zarfı (TÜBİTAK 2209-B)

`stowed_envelope_diameter_m`, tekerlek/şasi üzerinde katlanmış pervanenin
hedeflenen **depolama zarf çapı**dır (metre). TÜBİTAK 2209-B önerisinde tam açık
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
- `concept_throttle_sweep_*.png` — throttle panel (deployment progression)
- `concept_variant_compare_thr_*.png` — RT65_35 … RT85_15 comparison

**Radial vs concept:**

| Aspect | Radial / effective-diameter (analysis) | Concept deployment (presentation) |
|---|---|---|
| Purpose | D_eff analysis and validation | Folding/deployment explanation |
| Secondary angle | Model `theta_deg` | `display_hinge_angle_deg` |
| Start visual | Model angle at each state | Folded parallel baseline in static overview |

**Limitations:** not CAD, not CFD, not true airfoil geometry; illustrative blade
width and motor connection in V1.

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
