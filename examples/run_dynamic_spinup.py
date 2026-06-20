"""Run dynamic spin-up simulation and export CSV (V1 skeleton)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    MODEL_ASSUMPTIONS,
    SpinUpConfig,
    run_spinup_simulation,
    write_spinup_csv,
)
from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.foldable.variants import make_variant_config  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "foldable" / "dynamics" / "dynamic_spinup_RT75_25.csv"
ROOT_RATIO = 75
TIP_RATIO = 25


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

    states = run_spinup_simulation(
        variant_config,
        prop_entry,
        spinup=SpinUpConfig(dt_s=0.01, t_end_s=3.0),
    )
    written = write_spinup_csv(OUTPUT_PATH, states)

    print(f"Config  : {DEFAULT_CONFIG_PATH}")
    print(f"Variant : RT{ROOT_RATIO}_{TIP_RATIO} ({variant_config.id})")
    print(f"Output  : {written}")
    print(f"Rows    : {len(states)}")
    print()
    print("Model assumptions:")
    for note in MODEL_ASSUMPTIONS:
        print(f"  - {note}")
    print()
    print("First 10 rows:")
    header = (
        f"{'time_s':>8} {'thr':>5} {'rpm':>8} {'theta':>8} "
        f"{'D_eff':>8} {'thrust':>8} {'state':>15}"
    )
    print(header)
    for row in states[:10]:
        print(
            f"{row.time_s:8.3f} {row.throttle:5.1f} {row.rpm:8.1f} "
            f"{row.theta_deg:8.2f} {row.effective_diameter_m:8.4f} "
            f"{row.thrust_n:8.4f} {row.hinge_state:>15}"
        )


if __name__ == "__main__":
    main()
