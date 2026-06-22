"""Dynamic spin-up state container and CSV schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Sequence

SPINUP_CSV_COLUMNS: tuple[str, ...] = (
    "time_s",
    "throttle",
    "voltage_v",
    "current_a",
    "omega_rad_s",
    "rpm",
    "rotor_azimuth_deg",
    "theta_deg",
    "theta_dot_deg_s",
    "deployment_progress_01",
    "aero_effectiveness",
    "effective_diameter_m",
    "opening_moment_nm",
    "resisting_moment_nm",
    "motor_torque_nm",
    "aero_torque_nm",
    "thrust_n",
    "power_w",
    "hinge_state",
)


@dataclass(frozen=True)
class DynamicState:
    """Instantaneous dynamic spin-up state for CSV export and tests."""

    time_s: float
    throttle: float
    voltage_v: float
    current_a: float
    omega_rad_s: float
    rpm: float
    rotor_azimuth_deg: float
    theta_deg: float
    theta_dot_deg_s: float
    deployment_progress_01: float
    aero_effectiveness: float
    effective_diameter_m: float
    opening_moment_nm: float
    resisting_moment_nm: float
    motor_torque_nm: float
    aero_torque_nm: float
    thrust_n: float
    power_w: float
    hinge_state: str

    def to_csv_row(self) -> Dict[str, Any]:
        """Return a dict keyed by ``SPINUP_CSV_COLUMNS``."""
        row = asdict(self)
        return {col: row[col] for col in SPINUP_CSV_COLUMNS}
