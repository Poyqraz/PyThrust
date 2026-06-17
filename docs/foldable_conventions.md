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

## Çıktı Dosyaları

Sweep ve karşılaştırma tabloları `outputs/foldable/` altında CSV olarak
üretilir. Minimum sweep kolonları:

`rpm`, `theta_deg`, `effective_diameter_m`, `thrust_n`, `model_note`

Genişletilmiş kolonlar (ileride PyThrust entegrasyonu ile):

`voltage_v`, `throttle`, `torque_nm`, `current_a`, `power_w`, `efficiency`

## Model Sürümü

V1 modeli basitleştirilmiş ve kalibre edilebilir bir sayısal yaklaşımdır.
CFD, BEMT veya deneysel Ct/Cp verileri ileride aynı arayüz üzerinden
entegre edilebilir.
