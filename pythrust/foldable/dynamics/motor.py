"""Simple BLDC motor torque model for dynamic spin-up (algebraic current)."""

from __future__ import annotations

import math

from ..models import FoldablePropellerConfig


def _motor_kt_nm_per_a(kv_rpm_per_v: float) -> float:
    return 30.0 / (math.pi * kv_rpm_per_v)


def applied_voltage_v(throttle: float, config: FoldablePropellerConfig) -> float:
    """Motor bus voltage after throttle and discharge efficiency."""
    if throttle <= 0.0:
        return 0.0
    battery = config.battery
    return throttle * battery.voltage_v * battery.discharge_efficiency


def algebraic_motor_current(
    omega_rad_s: float,
    throttle: float,
    config: FoldablePropellerConfig,
) -> float:
    """Algebraic motor current (A); no electrical inductance in V1 skeleton."""
    if throttle <= 0.0:
        return 0.0

    motor = config.motor
    rpm = max(0.0, omega_rad_s * 30.0 / math.pi)
    v_applied = applied_voltage_v(throttle, config)
    v_back = rpm / motor.kv_rpm_per_v if motor.kv_rpm_per_v > 0.0 else 0.0
    r_total = motor.resistance_ohm + config.system.resistance_ohm
    if r_total <= 0.0:
        return 0.0
    i_raw = (v_applied - v_back) / r_total
    return max(0.0, min(motor.current_max_a, i_raw))


def motor_torque_nm(
    omega_rad_s: float,
    throttle: float,
    config: FoldablePropellerConfig,
) -> float:
    """Shaft torque from motor (N·m); zero when throttle is zero."""
    if throttle <= 0.0:
        return 0.0

    motor = config.motor
    rpm = max(0.0, omega_rad_s * 30.0 / math.pi)
    current_a = algebraic_motor_current(omega_rad_s, throttle, config)
    kt = _motor_kt_nm_per_a(motor.kv_rpm_per_v)
    i0 = motor.no_load_current_a if rpm <= 0.0 else _no_load_current_at_rpm(rpm, config)
    return kt * max(0.0, current_a - i0)


def _no_load_current_at_rpm(rpm: float, config: FoldablePropellerConfig) -> float:
    """No-load current using foldable motor config (linear model only in V1)."""
    motor = config.motor
    if rpm <= 0.0:
        return motor.no_load_current_a
    return motor.no_load_current_a
