"""Time-dependent dynamic spin-up model for foldable propeller (V1 skeleton)."""

from .aero import quasi_steady_aero
from .calibration import (
    TUBITAK_LIFT_REFERENCE_FRACTION,
    TUBITAK_LIFT_TARGET_FRACTION,
    TUBITAK_OPEN_DIAMETER_M,
    TUBITAK_PRETEST_RPM,
    TUBITAK_STOWED_ENVELOPE_DIAMETER_M,
    TubitakValidationSummary,
    tubitak_validation_summary,
)
from .dynamics_frame import (
    concept_frame_from_dynamic,
    parse_root_tip_ratios,
    rotor_azimuth_rad,
    visual_state_from_dynamic,
)
from .figures import plot_spinup_summary
from .frames import export_spinup_frames, spinup_frames_dir
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
    "TUBITAK_LIFT_REFERENCE_FRACTION",
    "TUBITAK_LIFT_TARGET_FRACTION",
    "TUBITAK_OPEN_DIAMETER_M",
    "TUBITAK_PRETEST_RPM",
    "TUBITAK_STOWED_ENVELOPE_DIAMETER_M",
    "DynamicState",
    "SpinUpConfig",
    "TubitakValidationSummary",
    "algebraic_motor_current",
    "applied_voltage_v",
    "concept_frame_from_dynamic",
    "default_rotor_inertia_kgm2",
    "default_throttle_schedule",
    "euler_step",
    "export_spinup_frames",
    "motor_torque_nm",
    "parse_root_tip_ratios",
    "plot_spinup_summary",
    "quasi_static_theta_deg",
    "quasi_steady_aero",
    "rotor_acceleration_rad_s2",
    "rotor_azimuth_rad",
    "run_spinup_simulation",
    "spinup_frames_dir",
    "tubitak_validation_summary",
    "visual_state_from_dynamic",
    "write_spinup_csv",
]
