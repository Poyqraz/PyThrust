"""Run dynamic spin-up simulation and export CSV, figures, and frames."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    IDEAL_GEOMETRY_RATIO_NOTE,
    MODEL_ASSUMPTIONS,
    SpinUpConfig,
    export_spinup_frames,
    plot_spinup_summary,
    run_spinup_simulation,
    spinup_checkpoint_summary,
    tubitak_validation_summary,
    write_spinup_csv,
    write_spinup_summary_csv,
)
from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.foldable.variants import make_variant_config  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "foldable" / "dynamics"
CSV_STEP_PATH = OUTPUT_DIR / "dynamic_spinup_RT75_25_step.csv"
CSV_RAMP_PATH = OUTPUT_DIR / "dynamic_spinup_RT75_25_ramp.csv"
CSV_LEGACY_PATH = OUTPUT_DIR / "dynamic_spinup_RT75_25.csv"
SUMMARY_STEP_PATH = OUTPUT_DIR / "dynamic_spinup_summary_RT75_25_step.csv"
SUMMARY_RAMP_PATH = OUTPUT_DIR / "dynamic_spinup_summary_RT75_25_ramp.csv"
SUMMARY_LEGACY_PATH = OUTPUT_DIR / "dynamic_spinup_summary_RT75_25.csv"
FIGURE_STEP_PATH = OUTPUT_DIR / "figures" / "spinup_RT75_25_step.png"
FIGURE_RAMP_PATH = OUTPUT_DIR / "figures" / "spinup_RT75_25_ramp.png"
FIGURE_LEGACY_PATH = OUTPUT_DIR / "figures" / "spinup_RT75_25.png"
VARIANT_LABEL = "RT75_25"
ROOT_RATIO = 75
TIP_RATIO = 25


def _print_first_rows(states, label: str) -> None:
    print(f"First 10 rows ({label}):")
    header = (
        f"{'time_s':>8} {'thr':>5} {'rpm':>8} {'theta':>8} "
        f"{'aero_eff':>8} {'D_eff':>8} {'thrust':>8} {'state':>15}"
    )
    print(header)
    for row in states[:10]:
        print(
            f"{row.time_s:8.3f} {row.throttle:5.1f} {row.rpm:8.1f} "
            f"{row.theta_deg:8.2f} {row.aero_effectiveness:8.3f} "
            f"{row.effective_diameter_m:8.4f} {row.thrust_n:8.4f} {row.hinge_state:>15}"
        )
    print()


def _print_checkpoint(label: str, checkpoint) -> None:
    print(f"Checkpoint @ 7100 rpm ({label}):")
    print(f"  time_to_7100_rpm                    : {checkpoint.time_to_7100_rpm}")
    print(f"  theta_at_7100_rpm                   : {checkpoint.theta_at_7100_rpm}")
    print(f"  D_eff_at_7100_rpm                   : {checkpoint.D_eff_at_7100_rpm}")
    print(f"  thrust_at_7100_rpm (model)          : {checkpoint.thrust_at_7100_rpm}")
    print(f"  reference_thrust_at_7100_rpm        : {checkpoint.reference_thrust_at_7100_rpm}")
    print(
        f"  ideal_geometry_ratio_at_7100_rpm    : "
        f"{checkpoint.ideal_geometry_ratio_at_7100_rpm}"
    )
    print(f"  current_pretest_ratio (TÜBİTAK)     : {checkpoint.current_pretest_ratio}")
    print(f"  project_target_ratio (TÜBİTAK)      : {checkpoint.project_target_ratio}")
    print(
        f"  current_calibrated_thrust_at_7100   : "
        f"{checkpoint.current_calibrated_thrust_at_7100_rpm}"
    )
    print(f"  target_thrust_at_7100_rpm           : {checkpoint.target_thrust_at_7100_rpm}")
    print(
        f"  current_calibrated_gap_to_target_%  : "
        f"{checkpoint.current_calibrated_gap_to_target_percent:.2f}"
    )
    print()


def main() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    variant_config = make_variant_config(config, ROOT_RATIO, TIP_RATIO)

    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(variant_config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit(
            f"Reference propeller '{variant_config.reference_propeller_id}' not found."
        )

    step_spinup = SpinUpConfig(dt_s=0.01, t_end_s=3.0, throttle_profile="step")
    ramp_spinup = SpinUpConfig(
        dt_s=0.01,
        t_end_s=3.0,
        throttle_profile="linear_ramp",
        ramp_time_s=0.5,
    )

    step_states = run_spinup_simulation(variant_config, prop_entry, spinup=step_spinup)
    ramp_states = run_spinup_simulation(variant_config, prop_entry, spinup=ramp_spinup)

    step_csv = write_spinup_csv(CSV_STEP_PATH, step_states)
    ramp_csv = write_spinup_csv(CSV_RAMP_PATH, ramp_states)
    legacy_csv = write_spinup_csv(CSV_LEGACY_PATH, step_states)

    step_checkpoint = spinup_checkpoint_summary(step_states, variant_config, prop_entry)
    ramp_checkpoint = spinup_checkpoint_summary(ramp_states, variant_config, prop_entry)
    summary_step = write_spinup_summary_csv(SUMMARY_STEP_PATH, step_checkpoint)
    summary_ramp = write_spinup_summary_csv(SUMMARY_RAMP_PATH, ramp_checkpoint)
    summary_legacy = write_spinup_summary_csv(SUMMARY_LEGACY_PATH, step_checkpoint)

    figure_step = plot_spinup_summary(
        step_states,
        FIGURE_STEP_PATH,
        variant_label=VARIANT_LABEL,
        throttle_profile="step",
        checkpoint=step_checkpoint,
    )
    figure_ramp = plot_spinup_summary(
        ramp_states,
        FIGURE_RAMP_PATH,
        variant_label=VARIANT_LABEL,
        throttle_profile="linear_ramp",
        ramp_time_s=ramp_spinup.ramp_time_s,
        checkpoint=ramp_checkpoint,
    )
    figure_legacy = plot_spinup_summary(
        step_states,
        FIGURE_LEGACY_PATH,
        variant_label=VARIANT_LABEL,
        throttle_profile="step",
        checkpoint=step_checkpoint,
    )

    step_frames = export_spinup_frames(
        step_states,
        variant_config,
        OUTPUT_DIR,
        variant_label=VARIANT_LABEL,
        throttle_profile="step",
    )
    ramp_frames = export_spinup_frames(
        ramp_states,
        variant_config,
        OUTPUT_DIR,
        variant_label=VARIANT_LABEL,
        throttle_profile="linear_ramp",
        ramp_time_s=ramp_spinup.ramp_time_s,
        profile_suffix="ramp",
    )
    validation = tubitak_validation_summary(step_states, variant_config)

    print(f"Config  : {DEFAULT_CONFIG_PATH}")
    print(f"Variant : {VARIANT_LABEL} ({variant_config.id})")
    print(f"Step CSV: {step_csv}")
    print(f"Ramp CSV: {ramp_csv}")
    print(f"Legacy  : {legacy_csv} (step profile, backward compatible)")
    print(f"Summary : step={summary_step}, ramp={summary_ramp}, legacy={summary_legacy}")
    print(f"Figures : step={figure_step}, ramp={figure_ramp}, legacy={figure_legacy}")
    print(f"Frames  : step={len(step_frames)} under {OUTPUT_DIR / 'frames' / VARIANT_LABEL}")
    print(
        f"          ramp={len(ramp_frames)} under "
        f"{OUTPUT_DIR / 'frames' / f'{VARIANT_LABEL}_ramp'}"
    )
    print(f"Rows    : step={len(step_states)}, ramp={len(ramp_states)}")
    print()
    print("Model assumptions:")
    for note in MODEL_ASSUMPTIONS:
        print(f"  - {note}")
    print()
    print("TÜBİTAK validation hooks:")
    for line in validation.to_lines():
        print(f"  - {line}")
    print()
    _print_checkpoint("step profile; ideal model vs calibrated references", step_checkpoint)
    _print_checkpoint("ramp profile; ideal model vs calibrated references", ramp_checkpoint)
    print(f"Note: {IDEAL_GEOMETRY_RATIO_NOTE}")
    print()
    _print_first_rows(step_states, "step")
    _print_first_rows(ramp_states, "linear_ramp, ramp_time_s=0.5")


if __name__ == "__main__":
    main()
