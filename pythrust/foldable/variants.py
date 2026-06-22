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
    base_tip_fraction: float | None = None,
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
    tip_segment_cg_from_hinge_m = tip_segment_length_m / 2.0

    scaled_mass_kg = tip_segment_mass_kg
    if base_tip_fraction is not None and base_tip_fraction > 0.0:
        scaled_mass_kg = tip_segment_mass_kg * (tip_fraction / base_tip_fraction)

    return FoldableGeometry(
        diameter_open_m=diameter_open_m,
        main_blade_length_m=hinge_position_m,
        tip_segment_length_m=tip_segment_length_m,
        hinge_position_m=hinge_position_m,
        tip_segment_mass_kg=scaled_mass_kg,
        blade_count=blade_count,
        tip_segment_cg_from_hinge_m=tip_segment_cg_from_hinge_m,
    )


def make_variant_config(
    base_config: FoldablePropellerConfig,
    root_ratio: int,
    tip_ratio: int,
) -> FoldablePropellerConfig:
    """Temel config'den kök/uç oranı varyantı oluştur."""
    base_open_radius_m = base_config.geometry.diameter_open_m / 2.0
    base_tip_fraction = base_config.geometry.tip_segment_length_m / base_open_radius_m
    geometry = geometry_from_root_tip_ratios(
        root_ratio,
        tip_ratio,
        diameter_open_m=base_config.geometry.diameter_open_m,
        tip_segment_mass_kg=base_config.geometry.tip_segment_mass_kg,
        blade_count=base_config.geometry.blade_count,
        base_tip_fraction=base_tip_fraction,
    )
    variant_id = variant_id_from_ratios(root_ratio, tip_ratio)
    description = (
        f"Uçtan mafsallı katlanabilir pervane — {root_ratio}/{tip_ratio} "
        f"kök/uç, açık çap {geometry.diameter_open_m:.2f} m"
    )
    hinge = replace(
        base_config.hinge,
        hinge_radius_m=geometry.hinge_position_m,
    )
    return replace(
        base_config,
        id=variant_id,
        description=description,
        geometry=geometry,
        hinge=hinge,
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
