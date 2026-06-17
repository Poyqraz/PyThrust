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
