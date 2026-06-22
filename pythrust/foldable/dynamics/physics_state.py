"""Physics debug state container and CSV schema for prescribed-RPM simulations."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

PHYSICS_DEBUG_CSV_COLUMNS: tuple[str, ...] = (
    "time_s",
    "rpm",
    "theta_deg",
    "theta_dot_deg_s",
    "theta_ddot_deg_s2",
    "tip_radial_extension_m",
    "geometric_effective_diameter_m",
    "aerodynamic_effective_diameter_m",
    "M_centrifugal_nm",
    "M_aero_nm",
    "M_stiffness_nm",
    "M_damping_nm",
    "M_friction_nm",
    "M_stop_nm",
    "M_net_nm",
    "thrust_root_n",
    "thrust_tip_n",
    "thrust_total_n",
    "hinge_state",
)


@dataclass(frozen=True)
class PhysicsState:
    """Single time step of propeller-first physics simulation."""

    time_s: float
    rpm: float
    theta_deg: float
    theta_dot_deg_s: float
    theta_ddot_deg_s2: float
    tip_radial_extension_m: float
    geometric_effective_diameter_m: float
    aerodynamic_effective_diameter_m: float
    M_centrifugal_nm: float
    M_aero_nm: float
    M_stiffness_nm: float
    M_damping_nm: float
    M_friction_nm: float
    M_stop_nm: float
    M_net_nm: float
    thrust_root_n: float
    thrust_tip_n: float
    thrust_total_n: float
    hinge_state: str

    def to_csv_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {col: row[col] for col in PHYSICS_DEBUG_CSV_COLUMNS}


def write_physics_csv(path: str | Path, states: Sequence[PhysicsState]) -> Path:
    """Write physics debug history to CSV."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PHYSICS_DEBUG_CSV_COLUMNS))
        writer.writeheader()
        for state in states:
            writer.writerow(state.to_csv_row())
    return output_path
