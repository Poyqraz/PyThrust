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
