"""Time-dependent dynamic spin-up model for foldable propeller (V1 skeleton)."""

from .aero import quasi_steady_aero
from .hinge import quasi_static_theta_deg
from .integrator import euler_step
from .motor import algebraic_motor_current, applied_voltage_v, motor_torque_nm
from .rotor import default_rotor_inertia_kgm2, rotor_acceleration_rad_s2
from .simulation import (
    MODEL_ASSUMPTIONS,
    SpinUpConfig,
    default_throttle_schedule,
    run_spinup_simulation,
    write_spinup_csv,
)
from .state import SPINUP_CSV_COLUMNS, DynamicState

__all__ = [
    "MODEL_ASSUMPTIONS",
    "SPINUP_CSV_COLUMNS",
    "DynamicState",
    "SpinUpConfig",
    "algebraic_motor_current",
    "applied_voltage_v",
    "default_rotor_inertia_kgm2",
    "default_throttle_schedule",
    "euler_step",
    "motor_torque_nm",
    "quasi_static_theta_deg",
    "quasi_steady_aero",
    "rotor_acceleration_rad_s2",
    "run_spinup_simulation",
    "write_spinup_csv",
]
