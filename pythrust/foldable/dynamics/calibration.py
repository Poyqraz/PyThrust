"""TÜBİTAK proposal reference targets and dynamic spin-up validation hooks."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from pythrust.propellers.database import PropellerEntry

from ..models import FoldablePropellerConfig
from .aero import reference_propeller_thrust_n
from .state import DynamicState

TUBITAK_OPEN_DIAMETER_M = 0.25
TUBITAK_STOWED_ENVELOPE_DIAMETER_M = 0.14
TUBITAK_PRETEST_RPM = 7100.0
TUBITAK_LIFT_REFERENCE_FRACTION = 0.70
TUBITAK_LIFT_TARGET_FRACTION = 0.85

SPINUP_SUMMARY_CSV_COLUMNS: tuple[str, ...] = (
    "variant_id",
    "checkpoint_rpm",
    "time_to_7100_rpm",
    "theta_at_7100_rpm",
    "D_eff_at_7100_rpm",
    "thrust_at_7100_rpm",
    "reference_thrust_at_7100_rpm",
    "thrust_ratio_at_7100_rpm",
    "current_pretest_ratio_target",
    "project_target_ratio",
)


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
            f"Open diameter target     : {self.open_diameter_m:.3f} m (fully deployed)",
            f"Stowed envelope target   : {self.stowed_envelope_diameter_m:.3f} m "
            "(storage envelope; not D_eff during flight)",
            f"Pretest RPM target       : {self.pretest_rpm_target:.0f} rpm",
            f"Max simulated RPM        : {self.max_rpm:.1f} rpm "
            f"({100.0 * self.rpm_fraction_of_pretest:.1f}% of pretest)",
            f"Max simulated thrust     : {self.max_thrust_n:.3f} N @ "
            f"{self.rpm_at_max_thrust:.0f} rpm",
            f"Max D_eff                : {self.max_d_eff_m:.4f} m "
            "(aerodynamic, not stowed envelope)",
            f"Folded-start theta       : {self.folded_start_theta_deg:.1f}°",
            f"Lift reference fraction  : {self.lift_reference_fraction:.0%} "
            "(pretest foldable vs same-diameter standard propeller)",
            f"Lift target fraction     : {self.lift_target_fraction:.0%} "
            "(project goal; future BEM/CFD/experiment calibration)",
        ]


@dataclass(frozen=True)
class SpinUpCheckpointSummary:
    """Single-row TÜBİTAK checkpoint at 7100 rpm."""

    variant_id: str
    checkpoint_rpm: float
    time_to_7100_rpm: float | None
    theta_at_7100_rpm: float | None
    D_eff_at_7100_rpm: float | None
    thrust_at_7100_rpm: float | None
    reference_thrust_at_7100_rpm: float
    thrust_ratio_at_7100_rpm: float | None
    current_pretest_ratio_target: float
    project_target_ratio: float

    def to_csv_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {col: row[col] for col in SPINUP_SUMMARY_CSV_COLUMNS}


def _lerp(a: float, b: float, fraction: float) -> float:
    return a + fraction * (b - a)


def _interpolate_at_rpm(
    states: Sequence[DynamicState],
    target_rpm: float,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Interpolate time, theta, D_eff, thrust at ``target_rpm``."""
    if not states or target_rpm <= 0.0:
        return None, None, None, None

    if states[0].rpm >= target_rpm:
        row = states[0]
        return row.time_s, row.theta_deg, row.effective_diameter_m, row.thrust_n

    for previous, current in zip(states, states[1:]):
        if previous.rpm < target_rpm <= current.rpm:
            span = current.rpm - previous.rpm
            if span <= 0.0:
                return current.time_s, current.theta_deg, current.effective_diameter_m, current.thrust_n
            fraction = (target_rpm - previous.rpm) / span
            return (
                _lerp(previous.time_s, current.time_s, fraction),
                _lerp(previous.theta_deg, current.theta_deg, fraction),
                _lerp(previous.effective_diameter_m, current.effective_diameter_m, fraction),
                _lerp(previous.thrust_n, current.thrust_n, fraction),
            )

    return None, None, None, None


def spinup_checkpoint_summary(
    states: Sequence[DynamicState],
    config: FoldablePropellerConfig,
    prop_entry: PropellerEntry,
    *,
    checkpoint_rpm: float = TUBITAK_PRETEST_RPM,
    rho: float = 1.225,
) -> SpinUpCheckpointSummary:
    """Build TÜBİTAK checkpoint row at 7100 rpm (or configured checkpoint)."""
    if not states:
        raise ValueError("states must not be empty.")

    reference_diameter_m = config.geometry.diameter_open_m
    reference_thrust = reference_propeller_thrust_n(
        checkpoint_rpm,
        reference_diameter_m,
        prop_entry,
        rho=rho,
    )
    time_s, theta_deg, d_eff, thrust = _interpolate_at_rpm(states, checkpoint_rpm)
    ratio = None
    if thrust is not None and reference_thrust > 0.0:
        ratio = thrust / reference_thrust

    return SpinUpCheckpointSummary(
        variant_id=config.id,
        checkpoint_rpm=checkpoint_rpm,
        time_to_7100_rpm=time_s,
        theta_at_7100_rpm=theta_deg,
        D_eff_at_7100_rpm=d_eff,
        thrust_at_7100_rpm=thrust,
        reference_thrust_at_7100_rpm=reference_thrust,
        thrust_ratio_at_7100_rpm=ratio,
        current_pretest_ratio_target=TUBITAK_LIFT_REFERENCE_FRACTION,
        project_target_ratio=TUBITAK_LIFT_TARGET_FRACTION,
    )


def write_spinup_summary_csv(
    path: str | Path,
    summary: SpinUpCheckpointSummary,
) -> Path:
    """Write single-row checkpoint summary CSV."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SPINUP_SUMMARY_CSV_COLUMNS))
        writer.writeheader()
        writer.writerow(summary.to_csv_row())
    return output_path


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
