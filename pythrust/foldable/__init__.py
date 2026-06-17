"""Katlanabilir pervane analiz modülü (TÜBİTAK 2209-B)."""

from .effective_diameter import effective_diameter_m
from .integration import (
    FoldableOperatingPointResult,
    evaluate_foldable_operating_point,
    post_process_from_operating_point,
    solve_pythrust_operating_point,
)
from .kinematics import theta_deg_from_rpm
from .models import (
    CalibrationConfig,
    FoldableGeometry,
    FoldablePropellerConfig,
    FoldableSweepRow,
    HingeConfig,
    KinematicsConfig,
    load_config,
)
from .performance import estimate_thrust_n, evaluate_sweep, evaluate_sweep_row
from .validation import (
    OPERATING_POINT_COLUMNS,
    SWEEP_COLUMNS,
    validate_operating_point_columns,
    validate_sweep_columns,
    write_operating_point_csv,
    write_sweep_csv,
)

__all__ = [
    "CalibrationConfig",
    "FoldableGeometry",
    "FoldableOperatingPointResult",
    "FoldablePropellerConfig",
    "FoldableSweepRow",
    "HingeConfig",
    "KinematicsConfig",
    "OPERATING_POINT_COLUMNS",
    "SWEEP_COLUMNS",
    "effective_diameter_m",
    "estimate_thrust_n",
    "evaluate_foldable_operating_point",
    "evaluate_sweep",
    "evaluate_sweep_row",
    "load_config",
    "post_process_from_operating_point",
    "solve_pythrust_operating_point",
    "theta_deg_from_rpm",
    "validate_operating_point_columns",
    "validate_sweep_columns",
    "write_operating_point_csv",
    "write_sweep_csv",
]
