"""TÜBİTAK proposal reference targets and dynamic spin-up validation hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..models import FoldablePropellerConfig
from .state import DynamicState

TUBITAK_OPEN_DIAMETER_M = 0.25
TUBITAK_STOWED_ENVELOPE_DIAMETER_M = 0.14
TUBITAK_PRETEST_RPM = 7100.0
TUBITAK_LIFT_REFERENCE_FRACTION = 0.70
TUBITAK_LIFT_TARGET_FRACTION = 0.85


@dataclass(frozen=True)
class TubitakValidationSummary:
    """Compare dynamic spin-up peaks against proposal reference targets."""

    open_diameter_m: float
    stowed_envelope_diameter_m: float
    pretest_rpm_target: float
    lift_reference_fraction: float
    lift_target_fraction: float
    max_rpm: float
    max_thrust_n: float
    max_d_eff_m: float
    folded_start_theta_deg: float
    rpm_at_max_thrust: float

    @property
    def rpm_fraction_of_pretest(self) -> float:
        if self.pretest_rpm_target <= 0.0:
            return 0.0
        return self.max_rpm / self.pretest_rpm_target

    def to_lines(self) -> list[str]:
        return [
            f"Open diameter target     : {self.open_diameter_m:.3f} m",
            f"Stowed envelope target   : {self.stowed_envelope_diameter_m:.3f} m",
            f"Pretest RPM target       : {self.pretest_rpm_target:.0f} rpm",
            f"Max simulated RPM        : {self.max_rpm:.1f} rpm "
            f"({100.0 * self.rpm_fraction_of_pretest:.1f}% of pretest)",
            f"Max simulated thrust     : {self.max_thrust_n:.3f} N @ "
            f"{self.rpm_at_max_thrust:.0f} rpm",
            f"Max D_eff                : {self.max_d_eff_m:.4f} m",
            f"Folded-start theta       : {self.folded_start_theta_deg:.1f}°",
            f"Lift reference fraction  : {self.lift_reference_fraction:.0%} "
            "(future BEM/CFD/experiment calibration)",
            f"Lift target fraction     : {self.lift_target_fraction:.0%} "
            "(future BEM/CFD/experiment calibration)",
        ]


def tubitak_validation_summary(
    states: Sequence[DynamicState],
    config: FoldablePropellerConfig,
) -> TubitakValidationSummary:
    """Build a validation summary from simulation history and config."""
    if not states:
        raise ValueError("states must not be empty.")

    max_thrust_state = max(states, key=lambda row: row.thrust_n)
    stowed = config.geometry.stowed_envelope_diameter_m
    return TubitakValidationSummary(
        open_diameter_m=config.geometry.diameter_open_m,
        stowed_envelope_diameter_m=(
            stowed if stowed is not None else TUBITAK_STOWED_ENVELOPE_DIAMETER_M
        ),
        pretest_rpm_target=TUBITAK_PRETEST_RPM,
        lift_reference_fraction=TUBITAK_LIFT_REFERENCE_FRACTION,
        lift_target_fraction=TUBITAK_LIFT_TARGET_FRACTION,
        max_rpm=max(row.rpm for row in states),
        max_thrust_n=max_thrust_state.thrust_n,
        max_d_eff_m=max(row.effective_diameter_m for row in states),
        folded_start_theta_deg=states[0].theta_deg,
        rpm_at_max_thrust=max_thrust_state.rpm,
    )
