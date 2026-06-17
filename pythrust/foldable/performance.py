"""Basitleştirilmiş thrust ve performans tahmini (V1)."""

from __future__ import annotations

import math
from typing import Protocol

from .models import FoldablePropellerConfig, FoldableSweepRow
from .effective_diameter import effective_diameter_m
from .kinematics import theta_deg_from_rpm


class ThrustModel(Protocol):
    """İleride Ct/Cp, BEMT, CFD veya deneysel modeller için arayüz."""

    def thrust_n(
        self,
        rpm: float,
        effective_diameter_m: float,
        rho: float,
    ) -> float:
        ...


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

    İleride PyThrust ``PropulsionSolver`` veya Ct/Cp tabloları ile
    değiştirilebilir; aynı fonksiyon imzası korunur.
  """
    if rpm <= 0.0 or diameter_m <= 0.0:
        return 0.0

    n = rpm / 60.0
    return k_thrust * ct_ref * rho * (n ** 2) * (diameter_m ** 4)


def evaluate_sweep_row(
    rpm: float,
    config: FoldablePropellerConfig,
    *,
    rho: float = 1.225,
) -> FoldableSweepRow:
    """Tek RPM noktası için sweep satırı üret."""
    theta_deg = theta_deg_from_rpm(rpm, config)
    diameter_m = effective_diameter_m(theta_deg, config)
    thrust_n = estimate_thrust_n(
        rpm,
        diameter_m,
        rho=rho,
        ct_ref=config.calibration.ct_ref,
        k_thrust=config.calibration.k_thrust,
    )

    return FoldableSweepRow(
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=diameter_m,
        thrust_n=thrust_n,
        model_note=config.calibration.model_note,
    )


def evaluate_sweep(
    rpm_values: list[float],
    config: FoldablePropellerConfig,
    *,
    rho: float = 1.225,
) -> list[FoldableSweepRow]:
    """RPM listesi için sweep tablosu üret."""
    return [evaluate_sweep_row(rpm, config, rho=rho) for rpm in rpm_values]
