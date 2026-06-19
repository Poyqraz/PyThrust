"""Visualization state container for a single propeller configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropellerVisualState:
    """Instantaneous foldable propeller state for 2D schematic drawing."""

    variant_id: str
    root_ratio: int
    tip_ratio: int
    throttle: float
    rpm: float
    theta_deg: float
    effective_diameter_m: float
    opening_moment_nm: float
    resisting_moment_nm: float
    moment_margin_nm: float
    hinge_state: str
    foldable_thrust_n: float
    hinge_position_m: float
    tip_segment_length_m: float
    diameter_open_m: float = 0.25
    stowed_envelope_diameter_m: float | None = None
    blade_count: int = 2
    theta_min_deg: float = -45.0

    def __post_init__(self) -> None:
        if self.hinge_position_m <= 0.0:
            raise ValueError("hinge_position_m must be positive.")
        if self.tip_segment_length_m <= 0.0:
            raise ValueError("tip_segment_length_m must be positive.")
        if self.effective_diameter_m <= 0.0:
            raise ValueError("effective_diameter_m must be positive.")
