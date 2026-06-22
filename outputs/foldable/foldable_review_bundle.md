# Foldable Review Bundle

## 1. Current git status

```text
?? setuav_pythrust.egg-info/
```

## 2. Current git diff --name-only

```text
(no unstaged or staged tracked-file diff)
```

## 3. Current relevant tree

```text
pythrust/foldable/
  __init__.py
  comparison.py
  decision.py
  design_sweep.py
  effective_diameter.py
  integration.py
  kinematics.py
  models.py
  performance.py
  summary.py
  validation.py
  variants.py

configs/foldable/
  TIP_HINGED_250_V01.json

examples/
  run_design_variant_decision_matrix.py
  run_design_variant_summary.py
  run_design_variant_sweep.py
  run_fixed_vs_foldable_comparison.py
  run_foldable_operating_point.py
  run_foldable_sweep.py

tests/foldable/
  __init__.py
  test_comparison.py
  test_decision.py
  test_design_sweep.py
  test_effective_diameter.py
  test_integration.py
  test_kinematics.py
  test_performance.py
  test_reference_scaled_thrust.py
  test_summary.py
  test_validation.py

docs/
  foldable_conventions.md
```

## 4. All added/changed foldable-related files and purpose

| File | Purpose |
|---|---|
| `docs/foldable_conventions.md` | Units, angle convention, effective diameter convention, CSV output expectations |
| `configs/foldable/TIP_HINGED_250_V01.json` | Base foldable propeller configuration |
| `pythrust/foldable/__init__.py` | Public exports for foldable module |
| `pythrust/foldable/models.py` | Dataclasses and JSON loader for foldable configs/results |
| `pythrust/foldable/kinematics.py` | RPM-to-hinge-angle model |
| `pythrust/foldable/effective_diameter.py` | Geometric effective diameter model |
| `pythrust/foldable/performance.py` | Simplified and reference-scaled thrust models |
| `pythrust/foldable/integration.py` | PyThrust operating point integration and foldable post-processing |
| `pythrust/foldable/comparison.py` | Fixed-vs-foldable comparison at equal operating condition |
| `pythrust/foldable/variants.py` | Root/tip ratio variant generation and compactness helpers |
| `pythrust/foldable/design_sweep.py` | Parametric sweep across variants and throttle points |
| `pythrust/foldable/summary.py` | Summary metrics aggregated from design sweep CSV |
| `pythrust/foldable/decision.py` | Weighted decision support scores from summary CSV |
| `pythrust/foldable/validation.py` | CSV validation and write helpers |
| `examples/run_foldable_sweep.py` | Basic RPM sweep example |
| `examples/run_foldable_operating_point.py` | PyThrust operating point + foldable post-processing example |
| `examples/run_fixed_vs_foldable_comparison.py` | Fixed-vs-foldable comparison example |
| `examples/run_design_variant_sweep.py` | Variant/throttle parametric sweep example |
| `examples/run_design_variant_summary.py` | Summary CSV generation example |
| `examples/run_design_variant_decision_matrix.py` | Weighted decision matrix generation example |
| `tests/foldable/test_kinematics.py` | Kinematics tests |
| `tests/foldable/test_effective_diameter.py` | Effective diameter tests |
| `tests/foldable/test_performance.py` | Simplified performance tests |
| `tests/foldable/test_validation.py` | CSV validation/write tests |
| `tests/foldable/test_integration.py` | Integration tests |
| `tests/foldable/test_comparison.py` | Fixed-vs-foldable comparison tests |
| `tests/foldable/test_reference_scaled_thrust.py` | `reference_scaled` thrust model tests |
| `tests/foldable/test_design_sweep.py` | Variant sweep tests |
| `tests/foldable/test_summary.py` | Summary metric tests |
| `tests/foldable/test_decision.py` | Weighted decision matrix tests |
| `outputs/foldable/sweep_results.csv` | Basic RPM sweep output |
| `outputs/foldable/foldable_operating_point_results.csv` | Operating point output |
| `outputs/foldable/comparison_fixed_vs_foldable.csv` | Fixed-vs-foldable comparison output |
| `outputs/foldable/design_variant_sweep.csv` | Variant sweep output |
| `outputs/foldable/design_variant_summary.csv` | Variant summary output |
| `outputs/foldable/design_variant_decision_matrix.csv` | Weighted decision output |
| `outputs/foldable/foldable_review_bundle.md` | This review package |

## 5. Current data flow

### Base foldable flow

1. `configs/foldable/TIP_HINGED_250_V01.json`
2. `pythrust/foldable/models.py::load_config()`
3. Either:
   - direct RPM sweep via `performance.evaluate_sweep_row()` / `evaluate_sweep()`, or
   - PyThrust operating point via `integration.solve_pythrust_operating_point()`
4. `kinematics.theta_deg_from_rpm()`
5. `effective_diameter.effective_diameter_m()`
6. `performance.estimate_foldable_thrust_n()`
7. CSV writing through `validation.py`

### Fixed-vs-foldable comparison flow

1. Base config + reference propeller ID
2. PyThrust solves fixed propeller operating point
3. Foldable post-processing uses same RPM/electrical equilibrium
4. Foldable thrust is estimated with selected model
5. Percent thrust difference is reported

### Variant sweep flow

1. Base config
2. `variants.make_variant_config()` generates 65/35, 70/30, 75/25, 80/20, 85/15
3. For each variant and throttle:
   - solve PyThrust operating point
   - compute `theta_deg`
   - compute `effective_diameter_m`
   - compute foldable thrust
   - attach fixed thrust and compactness ratio
4. Write `outputs/foldable/design_variant_sweep.csv`

### Summary flow

1. Read `outputs/foldable/design_variant_sweep.csv`
2. Group rows by `variant_id`
3. Aggregate:
   - folded diameter ratio
   - compactness gain percent
   - thrust deltas at 0.2 / 0.6 / 1.0
   - mean thrust difference percent
   - min/max effective diameter
   - simple score
4. Write `outputs/foldable/design_variant_summary.csv`

### Decision matrix flow

1. Read `outputs/foldable/design_variant_summary.csv`
2. Normalize:
   - compactness gain (higher better)
   - thrust preservation (mean thrust difference closer to 0 is better)
3. Compute weighted scores:
   - balanced: 50/50
   - flight priority: 30/70
   - ground priority: 70/30
4. Classify recommendation note
5. Write `outputs/foldable/design_variant_decision_matrix.csv`

## 6. Current model assumptions

### Global foldable assumptions

- No CFD, BEMT, CAD, or structural dynamics
- Hinge opening is represented only by a simple RPM-based kinematic law
- Aerodynamic impact of folding is represented only through effective diameter scaling
- Fixed propeller equilibrium comes from existing PyThrust solver and reference propeller database
- Foldable model is intentionally isolated from core PyThrust files

### Kinematics assumptions

- `theta_deg = 0` means fully open
- Negative `theta_deg` means folded/closing
- Below `rpm_threshold`, the blade is fully folded
- Above `rpm_full_open`, the blade is fully open
- In between, opening is linear

### Geometry assumptions

- Effective radius = hinge position + radial projection of tip segment
- `D_eff = 2 * (hinge_position + tip_length * cos(theta))`
- Open diameter is recovered at `theta = 0`

### Thrust assumptions

- `simple` model: `T = k_thrust * Ct_ref * rho * n^2 * D^4`
- `reference_scaled` model: `T_fold = T_fixed * (D_eff / D_ref)^4 * eta_hinge * eta_profile`
- `reference_scaled` is the currently used model for reportable comparisons

### Variant/compactness assumptions

- Open diameter is fixed at 0.25 m
- Root/tip split changes hinge radius and tip segment length
- `compactness_ratio` and `folded_diameter_ratio` both mean folded effective diameter / open diameter
- Lower folded diameter ratio means better compactness

### Current known modeling issue

- In `decision.py`, `ground_priority_score` currently mixes compactness with thrust preservation.
- This is physically wrong for stowed/ground mode because ground mode assumes the propeller is closed and no propeller thrust is expected.
- Ground mode should therefore not reward thrust preservation.

## 7. Requested source file contents

### `pythrust/foldable/models.py`

```python
"""Katlanabilir pervane konfigürasyon dataclass'ları ve JSON yükleyici."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FoldableGeometry:
    """Pervane geometri parametreleri (tüm uzunluklar metre)."""

    diameter_open_m: float
    main_blade_length_m: float
    tip_segment_length_m: float
    hinge_position_m: float
    tip_segment_mass_kg: float
    blade_count: int = 2


@dataclass(frozen=True)
class HingeConfig:
    """Mafsal ve açılma eşik parametreleri (açılar derece, RPM rev/min)."""

    theta_min_deg: float
    theta_max_deg: float
    rpm_threshold: float
    rpm_full_open: float


@dataclass(frozen=True)
class KinematicsConfig:
    """RPM → açı kinematik model parametreleri."""

    model: str
    k_open: float = 1.0


@dataclass(frozen=True)
class CalibrationConfig:
    """Basit ve referans ölçekli kalibrasyon katsayıları."""

    k_thrust: float
    k_torque: float
    ct_ref: float
    model_note: str
    thrust_model_mode: str = "simple"
    eta_hinge: float = 1.0
    eta_profile: float = 1.0
    reference_diameter_m: float = 0.254


@dataclass(frozen=True)
class MotorConfig:
    """Motor parametreleri — ileride PyThrust MotorSpec ile eşlenebilir."""

    kv_rpm_per_v: float
    resistance_ohm: float
    no_load_current_a: float
    current_max_a: float


@dataclass(frozen=True)
class BatteryConfig:
    """Batarya paketi parametreleri."""

    voltage_v: float
    discharge_efficiency: float = 1.0


@dataclass(frozen=True)
class SystemConfig:
    """Sistem iletim direnci."""

    resistance_ohm: float = 0.0


@dataclass(frozen=True)
class FoldablePropellerConfig:
    """Tam katlanabilir pervane konfigürasyonu."""

    id: str
    description: str
    geometry: FoldableGeometry
    hinge: HingeConfig
    kinematics: KinematicsConfig
    calibration: CalibrationConfig
    reference_propeller_id: str
    motor: MotorConfig
    battery: BatteryConfig
    system: SystemConfig


@dataclass(frozen=True)
class FoldableSweepRow:
    """Tek bir RPM noktası için sweep çıktı satırı."""

    rpm: float
    theta_deg: float
    effective_diameter_m: float
    thrust_n: float
    model_note: str
    voltage_v: float | None = None
    throttle: float | None = None
    torque_nm: float | None = None
    current_a: float | None = None
    power_w: float | None = None
    efficiency: float | None = None


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config field '{key}' must be an object.")
    return value


def load_config(path: str | Path) -> FoldablePropellerConfig:
    """JSON konfigürasyon dosyasını FoldablePropellerConfig olarak yükle."""
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))

    geometry_raw = _require_mapping(raw, "geometry")
    hinge_raw = _require_mapping(raw, "hinge")
    kinematics_raw = _require_mapping(raw, "kinematics")
    calibration_raw = _require_mapping(raw, "calibration")
    motor_raw = _require_mapping(raw, "motor")
    battery_raw = _require_mapping(raw, "battery")
    system_raw = _require_mapping(raw, "system")

    return FoldablePropellerConfig(
        id=str(raw["id"]),
        description=str(raw.get("description", "")),
        geometry=FoldableGeometry(
            diameter_open_m=float(geometry_raw["diameter_open_m"]),
            main_blade_length_m=float(geometry_raw["main_blade_length_m"]),
            tip_segment_length_m=float(geometry_raw["tip_segment_length_m"]),
            hinge_position_m=float(geometry_raw["hinge_position_m"]),
            tip_segment_mass_kg=float(geometry_raw["tip_segment_mass_kg"]),
            blade_count=int(geometry_raw.get("blade_count", 2)),
        ),
        hinge=HingeConfig(
            theta_min_deg=float(hinge_raw["theta_min_deg"]),
            theta_max_deg=float(hinge_raw["theta_max_deg"]),
            rpm_threshold=float(hinge_raw["rpm_threshold"]),
            rpm_full_open=float(hinge_raw["rpm_full_open"]),
        ),
        kinematics=KinematicsConfig(
            model=str(kinematics_raw.get("model", "linear_saturation")),
            k_open=float(kinematics_raw.get("k_open", 1.0)),
        ),
        calibration=CalibrationConfig(
            k_thrust=float(calibration_raw["k_thrust"]),
            k_torque=float(calibration_raw["k_torque"]),
            ct_ref=float(calibration_raw["ct_ref"]),
            model_note=str(calibration_raw["model_note"]),
            thrust_model_mode=str(calibration_raw.get("thrust_model_mode", "simple")),
            eta_hinge=float(calibration_raw.get("eta_hinge", 1.0)),
            eta_profile=float(calibration_raw.get("eta_profile", 1.0)),
            reference_diameter_m=float(calibration_raw.get("reference_diameter_m", 0.254)),
        ),
        reference_propeller_id=str(raw.get("reference_propeller_id", "")),
        motor=MotorConfig(
            kv_rpm_per_v=float(motor_raw["kv_rpm_per_v"]),
            resistance_ohm=float(motor_raw["resistance_ohm"]),
            no_load_current_a=float(motor_raw["no_load_current_a"]),
            current_max_a=float(motor_raw["current_max_a"]),
        ),
        battery=BatteryConfig(
            voltage_v=float(battery_raw["voltage_v"]),
            discharge_efficiency=float(battery_raw.get("discharge_efficiency", 1.0)),
        ),
        system=SystemConfig(
            resistance_ohm=float(system_raw.get("resistance_ohm", 0.0)),
        ),
    )
```

### `pythrust/foldable/kinematics.py`

```python
"""RPM'e bağlı uç segment açılma açısı hesabı."""

from __future__ import annotations

import math
from typing import Protocol

from .models import FoldablePropellerConfig, HingeConfig, KinematicsConfig


class HingeKinematicsModel(Protocol):
    """İleride BEMT/CFD/deneysel modeller için genişletilebilir arayüz."""

    def theta_deg(self, rpm: float) -> float:
        """Verilen RPM için uç segment açısını derece cinsinden döndür."""


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def theta_deg_from_hinge(
    rpm: float,
    hinge: HingeConfig,
    kinematics: KinematicsConfig,
) -> float:
    """RPM'e bağlı açılma açısını hesapla (derece).

    V1 modeli: doğrusal doygunluk (linear saturation).

    Fiziksel varsayım:
    - RPM, ``rpm_threshold`` altındayken pervane tam katlıdır (``theta_min_deg``).
    - RPM, ``rpm_full_open`` ve üzerindeyken pervane tam açıktır (``theta_max_deg``).
    - Aradaki bölgede merkezkaç etkisine bağlı açılma doğrusal yaklaşımla modellenir.
    - ``k_open`` kalibrasyon katsayısı ile deneysel veriye uyum sağlanabilir.

    Konvansiyon:
    - ``theta_deg = 0`` tam açık durum.
    - Negatif değerler katlanmış durum.
    """
    if rpm <= hinge.rpm_threshold:
        return hinge.theta_min_deg

    if rpm >= hinge.rpm_full_open:
        return hinge.theta_max_deg

    span = hinge.rpm_full_open - hinge.rpm_threshold
    if span <= 0.0:
        return hinge.theta_max_deg

    fraction = (rpm - hinge.rpm_threshold) / span
    fraction = _clamp(fraction * kinematics.k_open, 0.0, 1.0)
    theta_deg = hinge.theta_min_deg + fraction * (hinge.theta_max_deg - hinge.theta_min_deg)
    return _clamp(theta_deg, hinge.theta_min_deg, hinge.theta_max_deg)


def theta_deg_from_rpm(rpm: float, config: FoldablePropellerConfig) -> float:
    """Konfigürasyondan açılma açısını hesapla."""
    return theta_deg_from_hinge(rpm, config.hinge, config.kinematics)


def theta_rad_from_rpm(rpm: float, config: FoldablePropellerConfig) -> float:
    """İç hesaplamalar için radyan cinsinden açı."""
    return math.radians(theta_deg_from_rpm(rpm, config))
```

### `pythrust/foldable/effective_diameter.py`

```python
"""Açılma açısına bağlı efektif pervane çapı hesabı."""

from __future__ import annotations

import math
from typing import Protocol

from .models import FoldableGeometry, FoldablePropellerConfig


class EffectiveDiameterModel(Protocol):
    """İleride geometrik veya deneysel modeller için genişletilebilir arayüz."""

    def diameter_m(self, theta_deg: float) -> float:
        """Verilen açı için efektif çapı metre cinsinden döndür."""


def effective_diameter_from_geometry(
    theta_deg: float,
    geometry: FoldableGeometry,
) -> float:
    """Geometrik yaklaşımla efektif çapı hesapla (metre).

    V1 modeli:

        R_eff = hinge_position_m + tip_segment_length_m * cos(theta_rad)
        D_eff = 2 * R_eff

    Fiziksel varsayım:
    - Ana kanat gövdesi (hinge öncesi) sabit uzunluktadır.
    - Uç segment, mafsal etrafında dönerek radyal projeksiyonunu değiştirir.
    - ``theta_deg = 0`` (tam açık) durumunda ``D_eff = diameter_open_m``.
    - Negatif ``theta_deg`` değerlerinde uç segmentin radyal katkısı azalır.

    Not: ``hinge_position_m + tip_segment_length_m`` tam açıkta yarıçapı vermelidir;
    config dosyasında ``diameter_open_m = 2 * (hinge_position_m + tip_segment_length_m)``
    olacak şekilde tutulur.
    """
    theta_rad = math.radians(theta_deg)
    effective_radius_m = geometry.hinge_position_m + geometry.tip_segment_length_m * math.cos(
        theta_rad
    )
    return 2.0 * effective_radius_m


def effective_diameter_m(theta_deg: float, config: FoldablePropellerConfig) -> float:
    """Konfigürasyondan efektif çapı hesapla."""
    return effective_diameter_from_geometry(theta_deg, config.geometry)
```

### `pythrust/foldable/performance.py`

```python
"""Basitleştirilmiş thrust ve performans tahmini (V1)."""

from __future__ import annotations

from typing import Optional, Protocol

from .models import FoldablePropellerConfig, FoldableSweepRow
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm

THRUST_MODE_SIMPLE = "simple"
THRUST_MODE_REFERENCE_SCALED = "reference_scaled"


class ThrustModel(Protocol):
    """İleride Ct/Cp, BEMT, CFD veya deneysel modeller için arayüz."""

    def thrust_n(
        self,
        rpm: float,
        effective_diameter_m: float,
        rho: float,
    ) -> float:
        ...


def thrust_model_note(config: FoldablePropellerConfig) -> str:
    """Aktif itki modelini açıklayan kısa not."""
    calibration = config.calibration
    if calibration.thrust_model_mode == THRUST_MODE_REFERENCE_SCALED:
        return (
            "thrust_model=reference_scaled: "
            "T_fold = T_fixed * (D_eff/D_ref)^4 * eta_hinge * eta_profile"
        )
    return (
        "thrust_model=simple: T = k_thrust * Ct_ref * rho * n^2 * D^4 "
        "(not directly comparable to PyThrust Ct/Cp fixed thrust)"
    )


def estimate_thrust_n(
    rpm: float,
    diameter_m: float,
    *,
    rho: float = 1.225,
    ct_ref: float = 0.10,
    k_thrust: float = 1.0,
) -> float:
    """Basitleştirilmiş statik itki tahmini (N).

    V1 modeli — bilinçli olarak basitleştirilmiştir:

        T = k_thrust * Ct_ref * rho * n^2 * D^4

    burada ``n = RPM / 60`` (devir/saniye), ``D`` efektif çap (m).

    Bu model:
    - Gerçek pervane polarını (J, RPM) içermez.
    - İleri hız etkisini modellemez.
    - ``ct_ref`` ve ``k_thrust`` ile deneysel kalibrasyona açıktır.
    - PyThrust Ct/Cp sabit itki ile doğrudan bilimsel karşılaştırma için uygun değildir.

    İleride PyThrust ``PropulsionSolver`` veya Ct/Cp tabloları ile
    değiştirilebilir; aynı fonksiyon imzası korunur.
    """
    if rpm <= 0.0 or diameter_m <= 0.0:
        return 0.0

    n = rpm / 60.0
    return k_thrust * ct_ref * rho * (n ** 2) * (diameter_m ** 4)


def estimate_thrust_reference_scaled(
    fixed_thrust_n: float,
    effective_diameter_m: float,
    reference_diameter_m: float,
    *,
    eta_hinge: float = 1.0,
    eta_profile: float = 1.0,
) -> float:
    """Referans ölçekli katlanabilir itki tahmini (N).

        T_foldable = T_fixed * (D_eff / D_ref)^4 * eta_hinge * eta_profile

    ``T_fixed`` PyThrust OperatingPoint itki değerinden gelir; böylece aynı
    Ct/Cp tabanı üzerinde yalnızca efektif çap ve verim katsayılarıyla ölçeklenir.
    """
    if fixed_thrust_n <= 0.0 or reference_diameter_m <= 0.0:
        return 0.0

    ratio = effective_diameter_m / reference_diameter_m
    return fixed_thrust_n * (ratio ** 4) * eta_hinge * eta_profile


def estimate_foldable_thrust_n(
    config: FoldablePropellerConfig,
    rpm: float,
    effective_diameter_m: float,
    *,
    rho: float = 1.225,
    fixed_thrust_n: Optional[float] = None,
    reference_diameter_m: Optional[float] = None,
) -> float:
    """Config'e göre uygun katlanabilir itki modelini seç."""
    calibration = config.calibration
    mode = calibration.thrust_model_mode

    if mode == THRUST_MODE_SIMPLE:
        return estimate_thrust_n(
            rpm,
            effective_diameter_m,
            rho=rho,
            ct_ref=calibration.ct_ref,
            k_thrust=calibration.k_thrust,
        )

    if mode == THRUST_MODE_REFERENCE_SCALED:
        if fixed_thrust_n is None:
            raise ValueError("reference_scaled mode requires fixed_thrust_n from PyThrust.")
        d_ref = (
            reference_diameter_m
            if reference_diameter_m is not None
            else calibration.reference_diameter_m
        )
        return estimate_thrust_reference_scaled(
            fixed_thrust_n,
            effective_diameter_m,
            d_ref,
            eta_hinge=calibration.eta_hinge,
            eta_profile=calibration.eta_profile,
        )

    raise ValueError(f"Unknown thrust_model_mode: {mode!r}")


def evaluate_sweep_row(
    rpm: float,
    config: FoldablePropellerConfig,
    *,
    rho: float = 1.225,
    fixed_thrust_n: Optional[float] = None,
    reference_diameter_m: Optional[float] = None,
) -> FoldableSweepRow:
    """Tek RPM noktası için sweep satırı üret."""
    theta_deg = theta_deg_from_rpm(rpm, config)
    diameter_m = effective_diameter_m(theta_deg, config)
    thrust_n = estimate_foldable_thrust_n(
        config,
        rpm,
        diameter_m,
        rho=rho,
        fixed_thrust_n=fixed_thrust_n,
        reference_diameter_m=reference_diameter_m,
    )

    note = config.calibration.model_note
    if config.calibration.thrust_model_mode == THRUST_MODE_REFERENCE_SCALED:
        note = f"{note}; {thrust_model_note(config)}"

    return FoldableSweepRow(
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=diameter_m,
        thrust_n=thrust_n,
        model_note=note,
    )


def evaluate_sweep(
    rpm_values: list[float],
    config: FoldablePropellerConfig,
    *,
    rho: float = 1.225,
) -> list[FoldableSweepRow]:
    """RPM listesi için sweep tablosu üret."""
    return [evaluate_sweep_row(rpm, config, rho=rho) for rpm in rpm_values]
```

### `pythrust/foldable/integration.py`

```python
"""PyThrust operating point + foldable post-processing entegrasyonu (V2).

Mevcut ``PropulsionSolver`` çıktısından RPM ve elektromekanik durum okunur;
foldable modül bu RPM üzerinden açı, efektif çap ve itkiyi hesaplar.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from pythrust.propellers.database import PropellerEntry
from pythrust.propulsion.models import (
    BatterySpec,
    MotorSpec,
    OperatingPoint,
    PropellerSpec,
    SystemSpec,
)
from pythrust.propulsion.solver import PropulsionSolver

from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm
from .models import FoldablePropellerConfig
from .performance import estimate_foldable_thrust_n, thrust_model_note

V2_MODEL_NOTE = (
    "V2 PyThrust operating-point RPM + foldable post-processing "
    "(theta, D_eff, simplified thrust)"
)


@dataclass(frozen=True)
class FoldableOperatingPointResult:
    """PyThrust + foldable birleşik çalışma noktası çıktısı."""

    voltage_v: float
    throttle: float
    rpm: float
    theta_deg: float
    effective_diameter_m: float
    thrust_n: float
    torque_nm: float
    current_a: float
    power_w: float
    efficiency: float
    model_note: str
    is_feasible: bool = True
    infeasible_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Sonucu sözlük olarak döndür (CSV/raporlama için)."""
        return asdict(self)


def config_to_motor_spec(config: FoldablePropellerConfig) -> MotorSpec:
    """Foldable config motor alanlarını PyThrust MotorSpec'e dönüştür."""
    motor = config.motor
    return MotorSpec(
        kv_rpm_per_v=motor.kv_rpm_per_v,
        resistance_ohm=motor.resistance_ohm,
        no_load_current_a=motor.no_load_current_a,
        current_max_a=motor.current_max_a,
    )


def config_to_battery_spec(config: FoldablePropellerConfig) -> BatterySpec:
    """Foldable config batarya alanlarını PyThrust BatterySpec'e dönüştür."""
    battery = config.battery
    return BatterySpec(
        voltage_v=battery.voltage_v,
        discharge_efficiency=battery.discharge_efficiency,
    )


def config_to_system_spec(config: FoldablePropellerConfig) -> SystemSpec:
    """Foldable config sistem direncini PyThrust SystemSpec'e dönüştür."""
    return SystemSpec(resistance_ohm=config.system.resistance_ohm)


def config_to_propeller_spec(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
) -> PropellerSpec:
    """Referans pervane girişi ve config geometrisinden PropellerSpec üret.

    Solver denge RPM'i için veritabanındaki referans pervane çapı kullanılır;
    foldable post-processing aşamasında efektif çap ayrıca hesaplanır.
    """
    return PropellerSpec(
        diameter_m=prop_entry.diameter_m,
        blade_count=config.geometry.blade_count,
        pitch_m=prop_entry.pitch_m,
    )


def solve_pythrust_operating_point(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
) -> OperatingPoint:
    """Mevcut PyThrust solver ile denge çalışma noktasını çöz."""
    solver = PropulsionSolver()
    return solver.solve_operating_point(
        motor=config_to_motor_spec(config),
        battery=config_to_battery_spec(config),
        system=config_to_system_spec(config),
        propeller=config_to_propeller_spec(config, prop_entry),
        prop_entry=prop_entry,
        rho=rho,
        airspeed_mps=airspeed_mps,
        throttle=throttle,
    )


def post_process_from_operating_point(
    operating_point: OperatingPoint,
    config: FoldablePropellerConfig,
    throttle: float,
    voltage_v: float,
    *,
    rho: float = 1.225,
    model_note: Optional[str] = None,
) -> FoldableOperatingPointResult:
    """PyThrust OperatingPoint RPM'ini foldable post-processing ile genişlet.

    PyThrust'tan alınanlar:
    - ``rpm``, ``torque_nm``, ``motor_current_a``, ``battery_power_w``, ``system_efficiency``

    Foldable modülden hesaplananlar:
    - ``theta_deg``, ``effective_diameter_m``, ``thrust_n`` (config thrust model)
    """
    rpm = operating_point.rpm
    theta_deg = theta_deg_from_rpm(rpm, config)
    diameter_m = effective_diameter_m(theta_deg, config)
    thrust_n = estimate_foldable_thrust_n(
        config,
        rpm,
        diameter_m,
        rho=rho,
        fixed_thrust_n=operating_point.thrust_n,
        reference_diameter_m=config.calibration.reference_diameter_m,
    )

    note = model_note or V2_MODEL_NOTE
    note = f"{note}; {thrust_model_note(config)}"

    return FoldableOperatingPointResult(
        voltage_v=voltage_v,
        throttle=throttle,
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=diameter_m,
        thrust_n=thrust_n,
        torque_nm=operating_point.torque_nm,
        current_a=operating_point.motor_current_a,
        power_w=operating_point.battery_power_w,
        efficiency=operating_point.system_efficiency,
        model_note=note,
        is_feasible=operating_point.is_feasible,
        infeasible_reason=operating_point.infeasible_reason,
    )


def evaluate_foldable_operating_point(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> FoldableOperatingPointResult:
    """Tam V2 pipeline: PyThrust solver → foldable post-processing."""
    operating_point = solve_pythrust_operating_point(
        config,
        prop_entry,
        throttle,
        rho=rho,
        airspeed_mps=airspeed_mps,
    )
    return post_process_from_operating_point(
        operating_point,
        config,
        throttle,
        voltage_v=config.battery.voltage_v,
        rho=rho,
        model_note=model_note,
    )
```

### `pythrust/foldable/comparison.py`

```python
"""Sabit referans pervane vs katlanabilir pervane karşılaştırması."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

from pythrust.propellers.database import PropellerEntry

from .integration import (
    post_process_from_operating_point,
    solve_pythrust_operating_point,
)
from .models import FoldablePropellerConfig
from .performance import estimate_foldable_thrust_n, thrust_model_note
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm

COMPARISON_MODEL_NOTE_BASE = (
    "Fixed thrust from PyThrust OperatingPoint (reference propeller Ct/Cp); "
    "same motor/battery/throttle/RPM equilibrium for both"
)
COMPARISON_MODEL_NOTE = COMPARISON_MODEL_NOTE_BASE

COMPARISON_COLUMNS: tuple[str, ...] = (
    "voltage_v",
    "throttle",
    "rpm",
    "fixed_diameter_m",
    "foldable_effective_diameter_m",
    "fixed_thrust_n",
    "foldable_thrust_n",
    "thrust_difference_percent",
    "theta_deg",
    "model_note",
)


@dataclass(frozen=True)
class FixedVsFoldableComparisonRow:
    """Tek throttle noktası için sabit vs katlanabilir karşılaştırma satırı."""

    voltage_v: float
    throttle: float
    rpm: float
    fixed_diameter_m: float
    foldable_effective_diameter_m: float
    fixed_thrust_n: float
    foldable_thrust_n: float
    thrust_difference_percent: float
    theta_deg: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_thrust_difference_percent(
    fixed_thrust_n: float,
    foldable_thrust_n: float,
) -> float:
    """Foldable itkinin sabit referansa göre yüzde farkını hesapla.

    ``((foldable - fixed) / fixed) * 100``
    """
    if fixed_thrust_n <= 0.0:
        return 0.0
    return (foldable_thrust_n - fixed_thrust_n) / fixed_thrust_n * 100.0


def evaluate_fixed_vs_foldable_comparison(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> FixedVsFoldableComparisonRow:
    """Aynı çalışma koşulunda sabit ve katlanabilir sonuçları karşılaştır."""
    operating_point = solve_pythrust_operating_point(
        config,
        prop_entry,
        throttle,
        rho=rho,
        airspeed_mps=airspeed_mps,
    )
    foldable = post_process_from_operating_point(
        operating_point,
        config,
        throttle,
        voltage_v=config.battery.voltage_v,
        rho=rho,
    )

    fixed_thrust_n = operating_point.thrust_n
    d_eff = foldable.effective_diameter_m
    d_ref = config.calibration.reference_diameter_m
    foldable_thrust_n = estimate_foldable_thrust_n(
        config,
        operating_point.rpm,
        d_eff,
        rho=rho,
        fixed_thrust_n=fixed_thrust_n,
        reference_diameter_m=d_ref,
    )

    comparison_note = model_note or (
        f"{COMPARISON_MODEL_NOTE_BASE}; {thrust_model_note(config)}"
    )

    return FixedVsFoldableComparisonRow(
        voltage_v=config.battery.voltage_v,
        throttle=throttle,
        rpm=operating_point.rpm,
        fixed_diameter_m=prop_entry.diameter_m,
        foldable_effective_diameter_m=d_eff,
        fixed_thrust_n=fixed_thrust_n,
        foldable_thrust_n=foldable_thrust_n,
        thrust_difference_percent=compute_thrust_difference_percent(
            fixed_thrust_n,
            foldable_thrust_n,
        ),
        theta_deg=foldable.theta_deg,
        model_note=comparison_note,
    )


def compare_fixed_vs_foldable_sweep(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle_values: Sequence[float],
    *,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> List[FixedVsFoldableComparisonRow]:
    """Birden fazla throttle değeri için karşılaştırma tablosu üret."""
    return [
        evaluate_fixed_vs_foldable_comparison(
            config,
            prop_entry,
            throttle,
            rho=rho,
            airspeed_mps=airspeed_mps,
            model_note=model_note,
        )
        for throttle in throttle_values
    ]
```

### `pythrust/foldable/variants.py`

```python
"""Kök/uç oranına göre katlanabilir pervane tasarım varyantları."""

from __future__ import annotations

from dataclasses import replace
from typing import List, Sequence, Tuple

from .effective_diameter import effective_diameter_from_geometry
from .models import FoldableGeometry, FoldablePropellerConfig

DEFAULT_ROOT_TIP_RATIOS: Tuple[Tuple[int, int], ...] = (
    (65, 35),
    (70, 30),
    (75, 25),
    (80, 20),
    (85, 15),
)


def variant_id_from_ratios(root_ratio: int, tip_ratio: int) -> str:
    """Varyant kimliği üret (ör. ``TIP_HINGED_250_RT65_35``)."""
    return f"TIP_HINGED_250_RT{root_ratio}_{tip_ratio}"


def geometry_from_root_tip_ratios(
    root_ratio: int,
    tip_ratio: int,
    *,
    diameter_open_m: float = 0.25,
    tip_segment_mass_kg: float = 0.002,
    blade_count: int = 2,
) -> FoldableGeometry:
    """Açık çap sabitken kök/uç yüzde oranlarından geometri üret.

    ``root_ratio`` ve ``tip_ratio`` toplamı 100 olmalıdır. Yarıçap
    ``diameter_open_m / 2`` kök ve uç segment uzunluklarına bölünür.
    """
    if root_ratio + tip_ratio != 100:
        raise ValueError(f"root_ratio + tip_ratio must equal 100, got {root_ratio}+{tip_ratio}")

    open_radius_m = diameter_open_m / 2.0
    root_fraction = root_ratio / 100.0
    tip_fraction = tip_ratio / 100.0
    hinge_position_m = open_radius_m * root_fraction
    tip_segment_length_m = open_radius_m * tip_fraction

    return FoldableGeometry(
        diameter_open_m=diameter_open_m,
        main_blade_length_m=hinge_position_m,
        tip_segment_length_m=tip_segment_length_m,
        hinge_position_m=hinge_position_m,
        tip_segment_mass_kg=tip_segment_mass_kg,
        blade_count=blade_count,
    )


def make_variant_config(
    base_config: FoldablePropellerConfig,
    root_ratio: int,
    tip_ratio: int,
) -> FoldablePropellerConfig:
    """Temel config'den kök/uç oranı varyantı oluştur."""
    geometry = geometry_from_root_tip_ratios(
        root_ratio,
        tip_ratio,
        diameter_open_m=base_config.geometry.diameter_open_m,
        tip_segment_mass_kg=base_config.geometry.tip_segment_mass_kg,
        blade_count=base_config.geometry.blade_count,
    )
    variant_id = variant_id_from_ratios(root_ratio, tip_ratio)
    description = (
        f"Uçtan mafsallı katlanabilir pervane — {root_ratio}/{tip_ratio} "
        f"kök/uç, açık çap {geometry.diameter_open_m:.2f} m"
    )
    return replace(
        base_config,
        id=variant_id,
        description=description,
        geometry=geometry,
    )


def list_default_variant_configs(
    base_config: FoldablePropellerConfig,
    ratios: Sequence[Tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
) -> List[FoldablePropellerConfig]:
    """Varsayılan kök/uç oranları için varyant config listesi."""
    return [
        make_variant_config(base_config, root_ratio, tip_ratio)
        for root_ratio, tip_ratio in ratios
    ]


def folded_effective_diameter_m(config: FoldablePropellerConfig) -> float:
    """Tam katlı durumdaki (``theta_min_deg``) efektif çap."""
    return effective_diameter_from_geometry(
        config.hinge.theta_min_deg,
        config.geometry,
    )


def compactness_ratio(config: FoldablePropellerConfig) -> float:
    """Basit kompaktlık modeli: katlı efektif çap / açık çap."""
    open_diameter_m = config.geometry.diameter_open_m
    if open_diameter_m <= 0.0:
        return 0.0
    return folded_effective_diameter_m(config) / open_diameter_m
```

### `pythrust/foldable/design_sweep.py`

```python
"""Tasarım varyantı sweep — kök/uç oranı karşılaştırması."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pythrust.propellers.database import PropellerEntry

from .comparison import (
    COMPARISON_MODEL_NOTE_BASE,
    compute_thrust_difference_percent,
)
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm
from .integration import solve_pythrust_operating_point
from .models import FoldablePropellerConfig
from .performance import estimate_foldable_thrust_n, thrust_model_note
from .variants import (
    DEFAULT_ROOT_TIP_RATIOS,
    compactness_ratio,
    make_variant_config,
)

DESIGN_VARIANT_SWEEP_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "voltage_v",
    "throttle",
    "rpm",
    "theta_deg",
    "effective_diameter_m",
    "fixed_thrust_n",
    "foldable_thrust_n",
    "thrust_difference_percent",
    "compactness_ratio",
    "model_note",
)

DESIGN_VARIANT_MODEL_NOTE = (
    "Parametric root/tip ratio sweep; reference_scaled thrust; "
    "compactness_ratio = folded_effective_diameter / open_diameter"
)


@dataclass(frozen=True)
class DesignVariantSweepRow:
    """Tek varyant + throttle için tasarım karşılaştırma satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    voltage_v: float
    throttle: float
    rpm: float
    theta_deg: float
    effective_diameter_m: float
    fixed_thrust_n: float
    foldable_thrust_n: float
    thrust_difference_percent: float
    compactness_ratio: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_design_variant_row(
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle: float,
    *,
    root_ratio: int,
    tip_ratio: int,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
    model_note: Optional[str] = None,
) -> DesignVariantSweepRow:
    """Tek varyant ve throttle için sweep satırı üret."""
    operating_point = solve_pythrust_operating_point(
        config,
        prop_entry,
        throttle,
        rho=rho,
        airspeed_mps=airspeed_mps,
    )
    rpm = operating_point.rpm
    theta_deg = theta_deg_from_rpm(rpm, config)
    d_eff = effective_diameter_m(theta_deg, config)
    fixed_thrust_n = operating_point.thrust_n
    foldable_thrust_n = estimate_foldable_thrust_n(
        config,
        rpm,
        d_eff,
        rho=rho,
        fixed_thrust_n=fixed_thrust_n,
        reference_diameter_m=config.calibration.reference_diameter_m,
    )

    note = model_note or (
        f"{DESIGN_VARIANT_MODEL_NOTE}; {COMPARISON_MODEL_NOTE_BASE}; "
        f"{thrust_model_note(config)}"
    )

    return DesignVariantSweepRow(
        variant_id=config.id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        voltage_v=config.battery.voltage_v,
        throttle=throttle,
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=d_eff,
        fixed_thrust_n=fixed_thrust_n,
        foldable_thrust_n=foldable_thrust_n,
        thrust_difference_percent=compute_thrust_difference_percent(
            fixed_thrust_n,
            foldable_thrust_n,
        ),
        compactness_ratio=compactness_ratio(config),
        model_note=note,
    )


def sweep_design_variants(
    base_config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    throttle_values: Sequence[float],
    *,
    ratios: Sequence[Tuple[int, int]] = DEFAULT_ROOT_TIP_RATIOS,
    rho: float = 1.225,
    airspeed_mps: float = 0.0,
) -> List[DesignVariantSweepRow]:
    """Tüm varyantlar ve throttle noktaları için sweep tablosu."""
    rows: List[DesignVariantSweepRow] = []
    for root_ratio, tip_ratio in ratios:
        variant_config = make_variant_config(base_config, root_ratio, tip_ratio)
        for throttle in throttle_values:
            rows.append(
                evaluate_design_variant_row(
                    variant_config,
                    prop_entry,
                    throttle,
                    root_ratio=root_ratio,
                    tip_ratio=tip_ratio,
                    rho=rho,
                    airspeed_mps=airspeed_mps,
                )
            )
    return rows
```

### `pythrust/foldable/summary.py`

```python
"""Tasarım varyantı sweep özet metrikleri."""

from __future__ import annotations

import csv
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

DESIGN_VARIANT_SUMMARY_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "folded_diameter_ratio",
    "compactness_gain_percent",
    "thrust_diff_at_02",
    "thrust_diff_at_06",
    "thrust_diff_at_10",
    "mean_thrust_difference_percent",
    "min_effective_diameter_m",
    "max_effective_diameter_m",
    "score_simple",
    "model_note",
)

DESIGN_VARIANT_SUMMARY_MODEL_NOTE = (
    "Summary from design_variant_sweep.csv; folded_diameter_ratio = "
    "folded_effective_diameter / open_diameter (lower is more compact); "
    "compactness_gain_percent = (1 - folded_diameter_ratio) * 100; "
    "score_simple = compactness_gain_percent + mean_thrust_difference_percent"
)

THROTTLE_TOLERANCE = 1e-6
KEY_THROTTLES: tuple[tuple[str, float], ...] = (
    ("thrust_diff_at_02", 0.2),
    ("thrust_diff_at_06", 0.6),
    ("thrust_diff_at_10", 1.0),
)


@dataclass(frozen=True)
class DesignVariantSummaryRow:
    """Varyant başına özet karşılaştırma satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    folded_diameter_ratio: float
    compactness_gain_percent: float
    thrust_diff_at_02: float
    thrust_diff_at_06: float
    thrust_diff_at_10: float
    mean_thrust_difference_percent: float
    min_effective_diameter_m: float
    max_effective_diameter_m: float
    score_simple: float
    model_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compactness_gain_percent(folded_diameter_ratio: float) -> float:
    """Katlı çapın açık çapa göre yüzde küçülmesi (daha yüksek = daha kompakt)."""
    return (1.0 - folded_diameter_ratio) * 100.0


def score_simple(
    compactness_gain_percent_value: float,
    mean_thrust_difference_percent: float,
) -> float:
    """Basit denge skoru: kompaktlık kazancı + ortalama itki farkı (negatif)."""
    return compactness_gain_percent_value + mean_thrust_difference_percent


def _parse_sweep_row(row: Mapping[str, str]) -> Dict[str, Any]:
    return {
        "variant_id": row["variant_id"],
        "root_ratio": int(row["root_ratio"]),
        "tip_ratio": int(row["tip_ratio"]),
        "throttle": float(row["throttle"]),
        "effective_diameter_m": float(row["effective_diameter_m"]),
        "thrust_difference_percent": float(row["thrust_difference_percent"]),
        "compactness_ratio": float(row["compactness_ratio"]),
    }


def read_design_variant_sweep_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Sweep CSV dosyasını oku ve satır sözlükleri döndür."""
    sweep_path = Path(path)
    with sweep_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {sweep_path}")
        return [_parse_sweep_row(row) for row in reader]


def _thrust_diff_at_throttle(
    rows: Sequence[Mapping[str, Any]],
    throttle: float,
) -> float:
    for row in rows:
        if abs(float(row["throttle"]) - throttle) <= THROTTLE_TOLERANCE:
            return float(row["thrust_difference_percent"])
    raise ValueError(f"No sweep row found for throttle={throttle}")


def summarize_variant_rows(
    variant_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> DesignVariantSummaryRow:
    """Tek varyanta ait sweep satırlarından özet üret."""
    if not rows:
        raise ValueError(f"No sweep rows for variant '{variant_id}'")

    root_ratio = int(rows[0]["root_ratio"])
    tip_ratio = int(rows[0]["tip_ratio"])
    folded_diameter_ratio = float(rows[0]["compactness_ratio"])
    gain = compactness_gain_percent(folded_diameter_ratio)

    thrust_values = [float(row["thrust_difference_percent"]) for row in rows]
    mean_thrust = statistics.fmean(thrust_values)

    diameters = [float(row["effective_diameter_m"]) for row in rows]
    thrust_at = {
        field: _thrust_diff_at_throttle(rows, throttle)
        for field, throttle in KEY_THROTTLES
    }

    return DesignVariantSummaryRow(
        variant_id=variant_id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        folded_diameter_ratio=folded_diameter_ratio,
        compactness_gain_percent=gain,
        thrust_diff_at_02=thrust_at["thrust_diff_at_02"],
        thrust_diff_at_06=thrust_at["thrust_diff_at_06"],
        thrust_diff_at_10=thrust_at["thrust_diff_at_10"],
        mean_thrust_difference_percent=mean_thrust,
        min_effective_diameter_m=min(diameters),
        max_effective_diameter_m=max(diameters),
        score_simple=score_simple(gain, mean_thrust),
        model_note=model_note,
    )


def summarize_design_variants(
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> List[DesignVariantSummaryRow]:
    """Sweep satırlarını varyant başına gruplayıp özet tablo üret."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in sweep_rows:
        variant_id = str(row["variant_id"])
        grouped.setdefault(variant_id, []).append(dict(row))

    return [
        summarize_variant_rows(variant_id, grouped[variant_id], model_note=model_note)
        for variant_id in sorted(grouped)
    ]


def summarize_design_variants_from_csv(
    sweep_csv_path: str | Path,
    *,
    model_note: str = DESIGN_VARIANT_SUMMARY_MODEL_NOTE,
) -> List[DesignVariantSummaryRow]:
    """Sweep CSV dosyasından özet tablo üret."""
    return summarize_design_variants(
        read_design_variant_sweep_csv(sweep_csv_path),
        model_note=model_note,
    )


def validate_design_variant_summary_columns(columns: Sequence[str]) -> List[str]:
    """Özet CSV kolonlarını doğrula; eksikleri döndür."""
    return [col for col in DESIGN_VARIANT_SUMMARY_COLUMNS if col not in columns]


def write_design_variant_summary_csv(
    path: str | Path,
    rows: Sequence[DesignVariantSummaryRow],
    *,
    columns: Sequence[str] = DESIGN_VARIANT_SUMMARY_COLUMNS,
) -> Path:
    """Özet satırlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_design_variant_summary_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            payload = row.to_dict()
            writer.writerow({key: payload[key] for key in columns})

    return output_path
```

### `pythrust/foldable/decision.py`

```python
"""Tasarım varyantı ağırlıklı karar skorları."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

DESIGN_VARIANT_DECISION_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "root_ratio",
    "tip_ratio",
    "compactness_gain_percent",
    "mean_thrust_difference_percent",
    "performance_score",
    "compactness_score",
    "balanced_score",
    "flight_priority_score",
    "ground_priority_score",
    "recommendation_note",
)

RECOMMENDATION_COMPACT = "compact"
RECOMMENDATION_BALANCED = "balanced_candidate"
RECOMMENDATION_FLIGHT = "flight_priority"
RECOMMENDATION_NOT = "not_recommended"

VALID_RECOMMENDATIONS: frozenset[str] = frozenset(
    {
        RECOMMENDATION_COMPACT,
        RECOMMENDATION_BALANCED,
        RECOMMENDATION_FLIGHT,
        RECOMMENDATION_NOT,
    }
)

NOT_RECOMMENDED_THRESHOLD = 0.2
FALLBACK_RECOMMENDATION_THRESHOLD = 0.35

BALANCED_COMPACTNESS_WEIGHT = 0.5
BALANCED_PERFORMANCE_WEIGHT = 0.5
FLIGHT_COMPACTNESS_WEIGHT = 0.3
FLIGHT_PERFORMANCE_WEIGHT = 0.7
GROUND_COMPACTNESS_WEIGHT = 0.7
GROUND_PERFORMANCE_WEIGHT = 0.3


@dataclass(frozen=True)
class DesignVariantDecisionRow:
    """Varyant başına ağırlıklı karar skoru satırı."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    compactness_gain_percent: float
    mean_thrust_difference_percent: float
    performance_score: float
    compactness_score: float
    balanced_score: float
    flight_priority_score: float
    ground_priority_score: float
    recommendation_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def min_max_normalize(values: Sequence[float]) -> List[float]:
    """Değerleri [0, 1] aralığına ölçekle; yüksek ham değer = 1.0."""
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [1.0 for _ in values]
    span = vmax - vmin
    return [(value - vmin) / span for value in values]


def thrust_preservation_value(mean_thrust_difference_percent: float) -> float:
    """İtki korunumu: ortalama kayıp yüzdesi sıfıra ne kadar yakınsa o kadar iyi."""
    return mean_thrust_difference_percent


def weighted_score(
    compactness_score: float,
    performance_score: float,
    *,
    compactness_weight: float,
    performance_weight: float,
) -> float:
    """Ağırlıklı birleşik skor."""
    return (
        compactness_weight * compactness_score
        + performance_weight * performance_score
    )


def balanced_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=BALANCED_COMPACTNESS_WEIGHT,
        performance_weight=BALANCED_PERFORMANCE_WEIGHT,
    )


def flight_priority_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=FLIGHT_COMPACTNESS_WEIGHT,
        performance_weight=FLIGHT_PERFORMANCE_WEIGHT,
    )


def ground_priority_score(compactness_score: float, performance_score: float) -> float:
    return weighted_score(
        compactness_score,
        performance_score,
        compactness_weight=GROUND_COMPACTNESS_WEIGHT,
        performance_weight=GROUND_PERFORMANCE_WEIGHT,
    )


def _parse_summary_row(row: Mapping[str, str]) -> Dict[str, Any]:
    return {
        "variant_id": row["variant_id"],
        "root_ratio": int(row["root_ratio"]),
        "tip_ratio": int(row["tip_ratio"]),
        "compactness_gain_percent": float(row["compactness_gain_percent"]),
        "mean_thrust_difference_percent": float(row["mean_thrust_difference_percent"]),
    }


def read_design_variant_summary_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Özet CSV dosyasını oku."""
    summary_path = Path(path)
    with summary_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {summary_path}")
        return [_parse_summary_row(row) for row in reader]


def _argmax_variant(
    rows: Sequence[DesignVariantDecisionRow],
    attr: str,
) -> str:
    best = max(rows, key=lambda row: getattr(row, attr))
    return best.variant_id


def classify_recommendation(
    row: DesignVariantDecisionRow,
    *,
    compact_winner: str,
    balanced_winner: str,
    flight_winner: str,
) -> str:
    """Varyant için öneri sınıfı üret."""
    peak = max(
        row.balanced_score,
        row.flight_priority_score,
        row.ground_priority_score,
    )
    if peak < NOT_RECOMMENDED_THRESHOLD:
        return RECOMMENDATION_NOT

    if row.variant_id == compact_winner:
        return RECOMMENDATION_COMPACT
    if row.variant_id == flight_winner:
        return RECOMMENDATION_FLIGHT
    if row.variant_id == balanced_winner:
        return RECOMMENDATION_BALANCED

    if row.balanced_score >= FALLBACK_RECOMMENDATION_THRESHOLD:
        return RECOMMENDATION_BALANCED
    return RECOMMENDATION_NOT


def build_decision_matrix(
    summary_rows: Sequence[Mapping[str, Any]],
) -> List[DesignVariantDecisionRow]:
    """Özet satırlarından ağırlıklı karar matrisi üret."""
    if not summary_rows:
        return []

    compactness_values = [
        float(row["compactness_gain_percent"]) for row in summary_rows
    ]
    preservation_values = [
        thrust_preservation_value(float(row["mean_thrust_difference_percent"]))
        for row in summary_rows
    ]

    compactness_scores = min_max_normalize(compactness_values)
    performance_scores = min_max_normalize(preservation_values)

    preliminary: List[DesignVariantDecisionRow] = []
    for index, summary in enumerate(summary_rows):
        compactness_score = compactness_scores[index]
        performance_score = performance_scores[index]
        preliminary.append(
            DesignVariantDecisionRow(
                variant_id=str(summary["variant_id"]),
                root_ratio=int(summary["root_ratio"]),
                tip_ratio=int(summary["tip_ratio"]),
                compactness_gain_percent=float(summary["compactness_gain_percent"]),
                mean_thrust_difference_percent=float(
                    summary["mean_thrust_difference_percent"]
                ),
                performance_score=performance_score,
                compactness_score=compactness_score,
                balanced_score=balanced_score(compactness_score, performance_score),
                flight_priority_score=flight_priority_score(
                    compactness_score,
                    performance_score,
                ),
                ground_priority_score=ground_priority_score(
                    compactness_score,
                    performance_score,
                ),
                recommendation_note=RECOMMENDATION_NOT,
            )
        )

    compact_winner = _argmax_variant(preliminary, "ground_priority_score")
    flight_winner = _argmax_variant(preliminary, "flight_priority_score")
    remaining = [
        row
        for row in preliminary
        if row.variant_id not in {compact_winner, flight_winner}
    ]
    balanced_winner = (
        _argmax_variant(remaining, "balanced_score")
        if remaining
        else compact_winner
    )

    return [
        DesignVariantDecisionRow(
            variant_id=row.variant_id,
            root_ratio=row.root_ratio,
            tip_ratio=row.tip_ratio,
            compactness_gain_percent=row.compactness_gain_percent,
            mean_thrust_difference_percent=row.mean_thrust_difference_percent,
            performance_score=row.performance_score,
            compactness_score=row.compactness_score,
            balanced_score=row.balanced_score,
            flight_priority_score=row.flight_priority_score,
            ground_priority_score=row.ground_priority_score,
            recommendation_note=classify_recommendation(
                row,
                compact_winner=compact_winner,
                balanced_winner=balanced_winner,
                flight_winner=flight_winner,
            ),
        )
        for row in preliminary
    ]


def build_decision_matrix_from_csv(summary_csv_path: str | Path) -> List[DesignVariantDecisionRow]:
    """Özet CSV dosyasından karar matrisi üret."""
    return build_decision_matrix(read_design_variant_summary_csv(summary_csv_path))


def validate_design_variant_decision_columns(columns: Sequence[str]) -> List[str]:
    """Karar matrisi kolonlarını doğrula; eksikleri döndür."""
    return [col for col in DESIGN_VARIANT_DECISION_COLUMNS if col not in columns]


def write_design_variant_decision_csv(
    path: str | Path,
    rows: Sequence[DesignVariantDecisionRow],
    *,
    columns: Sequence[str] = DESIGN_VARIANT_DECISION_COLUMNS,
) -> Path:
    """Karar matrisi satırlarını CSV dosyasına yaz."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing = validate_design_variant_decision_columns(columns)
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            payload = row.to_dict()
            writer.writerow({key: payload[key] for key in columns})

    return output_path
```

### `configs/foldable/TIP_HINGED_250_V01.json`

```json
{
  "id": "TIP_HINGED_250_V01",
  "description": "Uçtan mafsallı katlanabilir pervane — 250 mm açık çap, V01",
  "geometry": {
    "diameter_open_m": 0.25,
    "main_blade_length_m": 0.10,
    "tip_segment_length_m": 0.025,
    "hinge_position_m": 0.10,
    "tip_segment_mass_kg": 0.002,
    "blade_count": 2
  },
  "hinge": {
    "theta_min_deg": -45.0,
    "theta_max_deg": 0.0,
    "rpm_threshold": 2000.0,
    "rpm_full_open": 8000.0
  },
  "kinematics": {
    "model": "linear_saturation",
    "k_open": 1.0
  },
  "calibration": {
    "k_thrust": 1.0,
    "k_torque": 1.0,
    "ct_ref": 0.10,
    "model_note": "V1 linear RPM hinge model, geometric D_eff",
    "thrust_model_mode": "reference_scaled",
    "eta_hinge": 1.0,
    "eta_profile": 1.0,
    "reference_diameter_m": 0.254
  },
  "reference_propeller_id": "APC_10x4.7SF",
  "motor": {
    "kv_rpm_per_v": 980.0,
    "resistance_ohm": 0.06,
    "no_load_current_a": 1.2,
    "current_max_a": 30.0
  },
  "battery": {
    "voltage_v": 11.1,
    "discharge_efficiency": 0.98
  },
  "system": {
    "resistance_ohm": 0.015
  }
}
```
