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
