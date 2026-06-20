"""Time-dependent dynamic spin-up model for foldable propeller (V1 skeleton)."""

from .aero import quasi_steady_aero, reference_propeller_thrust_n
from .aero_effectiveness import (
    FOLDED_MIN_AERO_EFFECTIVENESS,
    aero_effectiveness_from_progress,
    deployment_progress_from_theta,
)
from .calibration import (
    IDEAL_GEOMETRY_RATIO_NOTE,
    SPINUP_SUMMARY_CSV_COLUMNS,
    TUBITAK_LIFT_REFERENCE_FRACTION,
    TUBITAK_LIFT_TARGET_FRACTION,
    TUBITAK_OPEN_DIAMETER_M,
    TUBITAK_PRETEST_RPM,
    TUBITAK_STOWED_ENVELOPE_DIAMETER_M,
    SpinUpCheckpointSummary,
    TubitakValidationSummary,
    spinup_checkpoint_summary,
    tubitak_validation_summary,
    write_spinup_summary_csv,
)
from .dynamics_frame import (
    concept_frame_from_dynamic,
    parse_root_tip_ratios,
    rotor_azimuth_rad,
    visual_state_from_dynamic,
)
from .figures import SPINUP_REPORT_FIGURE_NOTE, plot_spinup_summary
from .frames import (
    SINGLE_ARM_CONCEPT_NOTE,
    export_spinup_frames,
    spinup_frames_dir,
)
from .hinge import initial_hinge_state, integrate_hinge_step, quasi_static_theta_deg
from .hinge_dynamics import HingeDynamicsMode, HingeState
from .hinge_moments import HingeMomentComponents, compute_hinge_moments
from .integrator import euler_step
from .motor import algebraic_motor_current, applied_voltage_v, motor_torque_nm
from .physics_figures import plot_physics_debug_figures
from .physics_simulation import run_prescribed_rpm_physics
from .physics_state import PHYSICS_DEBUG_CSV_COLUMNS, PhysicsState, write_physics_csv
from .prescribed_rpm import PrescribedRpmConfig
from .split_thrust import SplitThrustResult, compute_split_thrust
from .rotor import default_rotor_inertia_kgm2, rotor_acceleration_rad_s2
from .simulation import (
    MODEL_ASSUMPTIONS,
    SpinUpConfig,
    build_throttle_schedule,
    default_throttle_schedule,
    run_spinup_simulation,
    write_spinup_csv,
)
from .state import SPINUP_CSV_COLUMNS, DynamicState
from .throttle import ThrottleProfileName, throttle_at_time

__all__ = [
    "FOLDED_MIN_AERO_EFFECTIVENESS",
    "HingeDynamicsMode",
    "HingeMomentComponents",
    "HingeState",
    "IDEAL_GEOMETRY_RATIO_NOTE",
    "MODEL_ASSUMPTIONS",
    "PHYSICS_DEBUG_CSV_COLUMNS",
    "PhysicsState",
    "PrescribedRpmConfig",
    "SINGLE_ARM_CONCEPT_NOTE",
    "SPINUP_CSV_COLUMNS",
    "SPINUP_REPORT_FIGURE_NOTE",
    "SPINUP_SUMMARY_CSV_COLUMNS",
    "SplitThrustResult",
    "TUBITAK_LIFT_REFERENCE_FRACTION",
    "TUBITAK_LIFT_TARGET_FRACTION",
    "TUBITAK_OPEN_DIAMETER_M",
    "TUBITAK_PRETEST_RPM",
    "TUBITAK_STOWED_ENVELOPE_DIAMETER_M",
    "DynamicState",
    "SpinUpCheckpointSummary",
    "SpinUpConfig",
    "ThrottleProfileName",
    "TubitakValidationSummary",
    "aero_effectiveness_from_progress",
    "algebraic_motor_current",
    "applied_voltage_v",
    "build_throttle_schedule",
    "compute_hinge_moments",
    "compute_split_thrust",
    "concept_frame_from_dynamic",
    "default_rotor_inertia_kgm2",
    "default_throttle_schedule",
    "deployment_progress_from_theta",
    "euler_step",
    "export_spinup_frames",
    "initial_hinge_state",
    "integrate_hinge_step",
    "motor_torque_nm",
    "parse_root_tip_ratios",
    "plot_physics_debug_figures",
    "plot_spinup_summary",
    "quasi_static_theta_deg",
    "quasi_steady_aero",
    "reference_propeller_thrust_n",
    "rotor_acceleration_rad_s2",
    "rotor_azimuth_rad",
    "run_prescribed_rpm_physics",
    "run_spinup_simulation",
    "spinup_checkpoint_summary",
    "spinup_frames_dir",
    "throttle_at_time",
    "tubitak_validation_summary",
    "visual_state_from_dynamic",
    "write_physics_csv",
    "write_spinup_csv",
    "write_spinup_summary_csv",
]
