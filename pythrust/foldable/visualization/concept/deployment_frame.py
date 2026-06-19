"""Visualization-only deployment frame for concept schematics."""

from __future__ import annotations

from dataclasses import dataclass

from ..state import PropellerVisualState


@dataclass(frozen=True)
class ConceptDeploymentFrame:
    """Concept deployment geometry derived from model state (visualization only)."""

    source_state: PropellerVisualState
    deployment_progress_01: float
    display_hinge_angle_deg: float
    time_s: float | None = None

    @property
    def variant_id(self) -> str:
        return self.source_state.variant_id

    @property
    def throttle(self) -> float:
        return self.source_state.throttle

    @property
    def rpm(self) -> float:
        return self.source_state.rpm

    @property
    def theta_deg(self) -> float:
        return self.source_state.theta_deg

    @property
    def effective_diameter_m(self) -> float:
        return self.source_state.effective_diameter_m

    @property
    def opening_moment_nm(self) -> float:
        return self.source_state.opening_moment_nm

    @property
    def resisting_moment_nm(self) -> float:
        return self.source_state.resisting_moment_nm

    @property
    def hinge_state(self) -> str:
        return self.source_state.hinge_state

    @property
    def foldable_thrust_n(self) -> float:
        return self.source_state.foldable_thrust_n

    @property
    def hinge_position_m(self) -> float:
        return self.source_state.hinge_position_m

    @property
    def tip_segment_length_m(self) -> float:
        return self.source_state.tip_segment_length_m

    @property
    def diameter_open_m(self) -> float:
        return self.source_state.diameter_open_m

    @property
    def theta_min_deg(self) -> float:
        return self.source_state.theta_min_deg
