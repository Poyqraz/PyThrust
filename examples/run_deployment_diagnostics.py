"""Run deployment and tip-thrust physical diagnostics (CSV only, no new figures)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    resolve_foldable_evaluation_context,
    run_calibrated_thrust_split_diagnostic,
    run_deployment_bias_stiffness_sweep,
    run_foldable_candidate_ranking_v2,
    run_foldable_design_decision_matrix_v2,
    run_foldable_performance_summary_v2,
    run_motor_coupled_7100rpm_checkpoint_v2,
    run_motor_coupled_foldable_performance_v2,
    run_open_latch_diagnostic_cases,
    run_thrust_split_model_comparison,
    run_tip_thrust_activation_diagnostic,
    run_tip_thrust_latch_comparison,
    write_calibrated_thrust_split_diagnostic_csv,
    write_deployment_bias_stiffness_sweep_csv,
    write_foldable_candidate_ranking_v2_csv,
    write_foldable_design_decision_matrix_v2_csv,
    write_foldable_performance_summary_v2_csv,
    write_motor_coupled_7100rpm_checkpoint_v2_csv,
    write_motor_coupled_foldable_performance_v2_csv,
    write_thrust_split_model_comparison_csv,
    write_tip_thrust_activation_csv,
)
from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "foldable" / "dynamics" / "physics"


def main() -> None:
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit("Reference propeller not found.")

    eval_context = resolve_foldable_evaluation_context(config, prop_entry)

    sweep_rows = run_deployment_bias_stiffness_sweep(
        config, prop_entry, evaluation_context=eval_context
    )
    latch_rows = run_open_latch_diagnostic_cases(
        config, prop_entry, evaluation_context=eval_context
    )
    write_deployment_bias_stiffness_sweep_csv(
        str(OUTPUT_DIR / "deployment_bias_stiffness_sweep.csv"),
        [*sweep_rows, *latch_rows],
    )

    summary_rows = run_foldable_performance_summary_v2(
        config, prop_entry, context=eval_context
    )
    write_foldable_performance_summary_v2_csv(
        str(OUTPUT_DIR / "foldable_performance_summary_v2.csv"),
        summary_rows,
    )

    decision_rows = run_foldable_design_decision_matrix_v2(config, prop_entry)
    ranking_rows = run_foldable_candidate_ranking_v2(decision_rows)
    write_foldable_design_decision_matrix_v2_csv(
        str(OUTPUT_DIR / "foldable_design_decision_matrix_v2.csv"),
        decision_rows,
    )
    write_foldable_candidate_ranking_v2_csv(
        str(OUTPUT_DIR / "foldable_candidate_ranking_v2.csv"),
        ranking_rows,
    )

    motor_rows = run_motor_coupled_foldable_performance_v2(config, prop_entry)
    motor_checkpoint_rows = run_motor_coupled_7100rpm_checkpoint_v2(motor_rows)
    write_motor_coupled_foldable_performance_v2_csv(
        str(OUTPUT_DIR / "motor_coupled_foldable_performance_v2.csv"),
        motor_rows,
    )
    write_motor_coupled_7100rpm_checkpoint_v2_csv(
        str(OUTPUT_DIR / "motor_coupled_7100rpm_checkpoint_v2.csv"),
        motor_checkpoint_rows,
    )

    tip_rows = run_tip_thrust_activation_diagnostic(config, prop_entry)
    tip_latch_rows = run_tip_thrust_latch_comparison(config, prop_entry)
    write_tip_thrust_activation_csv(
        str(OUTPUT_DIR / "tip_thrust_activation_diagnostic.csv"),
        [*tip_rows, *tip_latch_rows],
    )

    split_rows = run_thrust_split_model_comparison(config, prop_entry)
    write_thrust_split_model_comparison_csv(
        str(OUTPUT_DIR / "thrust_split_model_comparison.csv"),
        split_rows,
    )

    calibrated_rows = run_calibrated_thrust_split_diagnostic(config, prop_entry)
    write_calibrated_thrust_split_diagnostic_csv(
        str(OUTPUT_DIR / "calibrated_thrust_split_diagnostic.csv"),
        calibrated_rows,
    )

    meaningful = [r for r in sweep_rows if r.reaches_meaningful_deployment_flag]
    open_stop = [r for r in [*sweep_rows, *latch_rows] if r.reaches_open_stop_flag]
    print(f"Deployment sweep : {len(sweep_rows)} cases, {len(meaningful)} meaningful")
    print(f"Open latch cases : {len(latch_rows)} cases, {len(open_stop)} open_stop")
    print(f"Performance v2   : {len(summary_rows)} rows")
    print(f"Decision matrix  : {len(decision_rows)} rows")
    print(f"Candidate rank   : {len(ranking_rows)} rows")
    print(f"Motor coupled    : {len(motor_rows)} rows, {len(motor_checkpoint_rows)} checkpoints")
    print(f"Tip activation   : {len(tip_rows) + len(tip_latch_rows)} cases")
    print(f"Split comparison : {len(split_rows)} rows")
    print(f"Calibrated split : {len(calibrated_rows)} rows")
    print(f"Output           : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
