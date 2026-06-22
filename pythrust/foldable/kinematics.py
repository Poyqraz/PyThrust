"""RPM ve moment dengesine bağlı uç segment açılma açısı hesabı.

Desteklenen modlar (``KinematicsConfig.kinematics_mode``):

- ``rpm_only``: doğrusal doygunluk (RPM eşikleri, geometriden bağımsız)
- ``moment_based``: merkezkaç açılma momenti ile mafsal yay/sürtünme dengesi

Moment V1 modeli::

    omega = rpm * 2π / 60
    M_open = m_tip * omega² * r_cg * lever_arm
    M_resist(theta) = k_hinge * (theta_rad - theta_min_rad) + M_friction

``r_cg`` = ``tip_segment_cg_from_hinge_m`` (yoksa ``tip_segment_length_m / 2``).
``lever_arm`` = ``tip_segment_length_m`` (V1 varsayımı).

``hinge_radius_m`` V1 açılma momentinde **kullanılmaz**; yalnızca config/metadata
olarak saklanır (varyant mafsal konumu ile hizalanır).
"""

from __future__ import annotations

import math
from typing import Protocol

from .models import FoldableGeometry, FoldablePropellerConfig, HingeConfig, KinematicsConfig

OPENING_MOMENT_V1_MODEL_NOTE = (
    "V1 moment model: hinge_radius_m is stored but not used in opening moment calculation."
)

MOMENT_MARGIN_NOTES: dict[str, str] = {
    "folded": "M_open <= M_resist at theta_min; margin ~ 0",
    "opening": "Equilibrium: M_open ~= M_resist; margin ~ 0",
    "fully_open": "Balanced at theta_max without mechanical stop",
    "saturated_open": "Positive margin: surplus M_open reacted by mechanical stop at theta_max",
}


class HingeKinematicsModel(Protocol):
    """İleride BEMT/CFD/deneysel modeller için genişletilebilir arayüz."""

    def theta_deg(self, rpm: float) -> float:
        """Verilen RPM için uç segment açısını derece cinsinden döndür."""


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def effective_tip_cg_from_hinge_m(geometry: FoldableGeometry) -> float:
    """Uç segment ağırlık merkezinin mafsaldan uzaklığı (m)."""
    if geometry.tip_segment_cg_from_hinge_m > 0.0:
        return geometry.tip_segment_cg_from_hinge_m
    return geometry.tip_segment_length_m / 2.0


def effective_hinge_radius_m(hinge: HingeConfig, geometry: FoldableGeometry) -> float:
    """Mafsalın dönüş ekseninden radyal mesafesi (m)."""
    if hinge.hinge_radius_m > 0.0:
        return hinge.hinge_radius_m
    return geometry.hinge_position_m


def opening_moment_nm(
    rpm: float,
    geometry: FoldableGeometry,
    _hinge: HingeConfig,
) -> float:
    """Merkezkaç kaynaklı açılma momenti (N·m).

    V1 formül: ``M_open = m_tip * omega² * r_cg * lever_arm``.

    ``hinge_radius_m`` bu hesapta kullanılmaz; bkz. ``OPENING_MOMENT_V1_MODEL_NOTE``.
    """
    if rpm <= 0.0:
        return 0.0

    omega = rpm * 2.0 * math.pi / 60.0
    r_cg = effective_tip_cg_from_hinge_m(geometry)
    lever_arm = geometry.tip_segment_length_m
    return geometry.tip_segment_mass_kg * omega**2 * r_cg * lever_arm


def resisting_moment_nm(theta_deg: float, hinge: HingeConfig) -> float:
    """Mafsal yay ve sürtünmeye karşı direnç momenti (N·m).

    ``hinge_stiffness_nm_per_rad`` ile açı farkı **radyan** cinsinden çarpılır.
    """
    theta_rad = math.radians(theta_deg)
    theta_min_rad = math.radians(hinge.theta_min_deg)
    return (
        hinge.hinge_stiffness_nm_per_rad * (theta_rad - theta_min_rad)
        + hinge.hinge_friction_nm
    )


PHYSICS_HINGE_STATE_NOTES: dict[str, str] = {
    "folded": "At theta_min, opening moment does not exceed resistance",
    "opening": "Transient or moving — not at rest equilibrium",
    "equilibrium_partial": "At rest between limits; M_cent + M_aero balances stiffness/friction",
    "open_stop": "At theta_max; held by mechanical stop/latch (not moment balance)",
}


def classify_physics_hinge_state(
    rpm: float,
    theta_deg: float,
    theta_dot_deg_s: float,
    opening_moment: float,
    resisting_moment: float,
    hinge: HingeConfig,
    *,
    angle_tol_deg: float = 0.5,
    velocity_tol_deg_s: float = 1.0,
) -> str:
    """V2 prescribed-RPM hinge state for physics path."""
    if rpm <= 0.0:
        return "folded"

    at_min = abs(theta_deg - hinge.theta_min_deg) <= angle_tol_deg
    at_max = abs(theta_deg - hinge.theta_max_deg) <= angle_tol_deg
    at_rest = abs(theta_dot_deg_s) <= velocity_tol_deg_s

    if at_max:
        return "open_stop"

    if at_min and at_rest and opening_moment <= resisting_moment + 1e-9:
        return "folded"

    if at_rest and not at_min:
        return "equilibrium_partial"

    return "opening"


def classify_hinge_state(
    rpm: float,
    theta_deg: float,
    opening_moment: float,
    resisting_moment: float,
    hinge: HingeConfig,
    *,
    angle_tol_deg: float = 1e-6,
) -> str:
    """Moment dengesi durum etiketi."""
    if rpm <= 0.0:
        return "folded"
    if abs(theta_deg - hinge.theta_min_deg) <= angle_tol_deg:
        if opening_moment <= resisting_moment + 1e-12:
            return "folded"
    if abs(theta_deg - hinge.theta_max_deg) <= angle_tol_deg:
        if opening_moment > resisting_moment + 1e-9:
            return "saturated_open"
        return "fully_open"
    return "opening"


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


def theta_deg_moment_based(rpm: float, config: FoldablePropellerConfig) -> float:
    """Geometriye bağlı moment dengesi ile açılma açısı (derece).

  Denge: ``M_open(rpm, geometry) = M_resist(theta)``; çözüm ``[theta_min, theta_max]``
  aralığına kısıtlanır.
    """
    hinge = config.hinge
    geometry = config.geometry

    if hinge.hinge_stiffness_nm_per_rad <= 0.0:
        raise ValueError("hinge_stiffness_nm_per_rad must be positive for moment_based mode.")

    m_open = opening_moment_nm(rpm, geometry, hinge)
    if m_open <= hinge.hinge_friction_nm:
        return hinge.theta_min_deg

    theta_min_rad = math.radians(hinge.theta_min_deg)
    theta_max_rad = math.radians(hinge.theta_max_deg)
    theta_rad = theta_min_rad + (m_open - hinge.hinge_friction_nm) / hinge.hinge_stiffness_nm_per_rad
    theta_rad = _clamp(theta_rad, theta_min_rad, theta_max_rad)
    return math.degrees(theta_rad)


def theta_deg_from_rpm(rpm: float, config: FoldablePropellerConfig) -> float:
    """Konfigürasyondan açılma açısını hesapla."""
    if config.kinematics.kinematics_mode == "moment_based":
        return theta_deg_moment_based(rpm, config)
    return theta_deg_from_hinge(rpm, config.hinge, config.kinematics)


def theta_rad_from_rpm(rpm: float, config: FoldablePropellerConfig) -> float:
    """İç hesaplamalar için radyan cinsinden açı."""
    return math.radians(theta_deg_from_rpm(rpm, config))
