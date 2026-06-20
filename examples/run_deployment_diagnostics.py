"""Run deployment and tip-thrust physical diagnostics (CSV only, no new figures)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    run_deployment_bias_stiffness_sweep,
    run_open_latch_diagnostic_cases,
    run_tip_thrust_activation_diagnostic,
    run_tip_thrust_latch_comparison,
    write_deployment_bias_stiffness_sweep_csv,
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

    sweep_rows = run_deployment_bias_stiffness_sweep(config, prop_entry)
    latch_rows = run_open_latch_diagnostic_cases(config, prop_entry)
    write_deployment_bias_stiffness_sweep_csv(
        str(OUTPUT_DIR / "deployment_bias_stiffness_sweep.csv"),
        [*sweep_rows, *latch_rows],
    )

    tip_rows = run_tip_thrust_activation_diagnostic(config, prop_entry)
    tip_latch_rows = run_tip_thrust_latch_comparison(config, prop_entry)
    write_tip_thrust_activation_csv(
        str(OUTPUT_DIR / "tip_thrust_activation_diagnostic.csv"),
        [*tip_rows, *tip_latch_rows],
    )

    meaningful = [r for r in sweep_rows if r.reaches_meaningful_deployment_flag]
    open_stop = [r for r in [*sweep_rows, *latch_rows] if r.reaches_open_stop_flag]
    print(f"Deployment sweep : {len(sweep_rows)} cases, {len(meaningful)} meaningful")
    print(f"Open latch cases : {len(latch_rows)} cases, {len(open_stop)} open_stop")
    print(f"Tip activation   : {len(tip_rows) + len(tip_latch_rows)} cases")
    print(f"Output           : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
