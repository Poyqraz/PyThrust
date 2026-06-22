"""Moment tabanlı mafsal kinematiği doğrulama CSV ve konsol tablosu üret."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable import load_config  # noqa: E402
from pythrust.foldable.decision import deployment_raw  # noqa: E402
from pythrust.foldable.moment_validation import (  # noqa: E402
    build_moment_kinematics_validation,
    build_variant_physical_parameters,
    format_validation_table,
    write_moment_kinematics_validation_csv,
    write_variant_physical_parameters_csv,
)
from pythrust.foldable.summary import summarize_design_variants_from_csv  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

THROTTLE_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]
VALIDATION_CSV = PROJECT_ROOT / "outputs" / "foldable" / "moment_kinematics_validation.csv"
PARAMETERS_CSV = PROJECT_ROOT / "outputs" / "foldable" / "variant_physical_parameters.csv"
SWEEP_CSV = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_sweep.csv"


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
    config = load_config(config_path)

    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit(
            f"Reference propeller '{config.reference_propeller_id}' not found in database."
        )

    validation_rows = build_moment_kinematics_validation(
        config,
        prop_entry,
        THROTTLE_VALUES,
    )
    parameter_rows = build_variant_physical_parameters(config)

    validation_path = write_moment_kinematics_validation_csv(VALIDATION_CSV, validation_rows)
    parameters_path = write_variant_physical_parameters_csv(PARAMETERS_CSV, parameter_rows)

    print(f"Config              : {config_path}")
    print(f"Kinematics mode     : {config.kinematics.kinematics_mode}")
    print(f"Validation CSV      : {validation_path}")
    print(f"Parameters CSV      : {parameters_path}")
    print()
    print("Moment validation table (all rows):")
    print(format_validation_table(validation_rows))
    print()
    print("diameter_growth / active_window_diameter_growth_score formula:")
    print("  deployment_raw = (max_effective_diameter_m - min_effective_diameter_m)")
    print("                   / max_effective_diameter_m")
    print("  (over sampled throttle window only; not stowed-to-open geometry)")
    print("  deployment_score = min-max normalize(deployment_raw)")
    print("  active_window_diameter_growth_score = deployment_score (CSV alias)")
    print()
    print(f"Opening moment V1 note: hinge_radius_m is NOT used.")
    print(f"  Formula: M_open = m_tip * omega^2 * r_cg * lever_arm")
    print()
    print("moment_margin_nm interpretation:")
    print("  opening: ~0 (equilibrium)")
    print("  saturated_open: positive (surplus M_open at mechanical stop)")
    print()

    if SWEEP_CSV.is_file():
        summary_rows = summarize_design_variants_from_csv(SWEEP_CSV)
        print("deployment_raw by variant (from existing sweep):")
        best_id = ""
        best_raw = -1.0
        for row in summary_rows:
            raw = deployment_raw(
                row.min_effective_diameter_m,
                row.max_effective_diameter_m,
            )
            print(
                f"  {row.variant_id}: min_D={row.min_effective_diameter_m:.4f}, "
                f"max_D={row.max_effective_diameter_m:.4f}, raw={raw:.4f}"
            )
            if raw > best_raw:
                best_raw = raw
                best_id = row.variant_id
        print(f"  max deployment_raw -> {best_id}")


if __name__ == "__main__":
    main()
