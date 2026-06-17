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
