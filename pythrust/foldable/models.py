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
    tip_segment_cg_from_hinge_m: float = 0.0
    stowed_envelope_diameter_m: float | None = None


@dataclass(frozen=True)
class HingeConfig:
    """Mafsal ve açılma eşik parametreleri (açılar derece, RPM rev/min)."""

    theta_min_deg: float
    theta_max_deg: float
    rpm_threshold: float
    rpm_full_open: float
    hinge_radius_m: float = 0.0
    hinge_stiffness_nm_per_rad: float = 0.008
    hinge_friction_nm: float = 0.0


@dataclass(frozen=True)
class KinematicsConfig:
    """RPM → açı kinematik model parametreleri."""

    model: str
    k_open: float = 1.0
    kinematics_mode: str = "rpm_only"


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

    tip_segment_length_m = float(geometry_raw["tip_segment_length_m"])
    hinge_position_m = float(geometry_raw["hinge_position_m"])
    tip_segment_cg_from_hinge_m = float(
        geometry_raw.get(
            "tip_segment_cg_from_hinge_m",
            tip_segment_length_m / 2.0,
        )
    )
    hinge_radius_m = float(hinge_raw.get("hinge_radius_m", hinge_position_m))
    kinematics_mode = str(kinematics_raw.get("kinematics_mode", "rpm_only"))
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
            tip_segment_length_m=tip_segment_length_m,
            hinge_position_m=hinge_position_m,
            tip_segment_mass_kg=float(geometry_raw["tip_segment_mass_kg"]),
            blade_count=int(geometry_raw.get("blade_count", 2)),
            tip_segment_cg_from_hinge_m=tip_segment_cg_from_hinge_m,
            stowed_envelope_diameter_m=(
                float(geometry_raw["stowed_envelope_diameter_m"])
                if geometry_raw.get("stowed_envelope_diameter_m") is not None
                else None
            ),
        ),
        hinge=HingeConfig(
            theta_min_deg=float(hinge_raw["theta_min_deg"]),
            theta_max_deg=float(hinge_raw["theta_max_deg"]),
            rpm_threshold=float(hinge_raw["rpm_threshold"]),
            rpm_full_open=float(hinge_raw["rpm_full_open"]),
            hinge_radius_m=hinge_radius_m,
            hinge_stiffness_nm_per_rad=float(
                hinge_raw.get("hinge_stiffness_nm_per_rad", 0.008)
            ),
            hinge_friction_nm=float(hinge_raw.get("hinge_friction_nm", 0.0)),
        ),
        kinematics=KinematicsConfig(
            model=str(kinematics_raw.get("model", "linear_saturation")),
            k_open=float(kinematics_raw.get("k_open", 1.0)),
            kinematics_mode=kinematics_mode,
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
