"""Sabit vs katlanabilir pervane karşılaştırma örneği.

Aynı voltaj/throttle koşullarında referans sabit pervane (PyThrust) ile
katlanabilir post-processing sonuçlarını karşılaştırır.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable import (  # noqa: E402
    compare_fixed_vs_foldable_sweep,
    load_config,
    write_comparison_csv,
)
from pythrust.propellers import PropellerDatabase  # noqa: E402

THROTTLE_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
    output_path = PROJECT_ROOT / "outputs" / "foldable" / "comparison_fixed_vs_foldable.csv"

    config = load_config(config_path)

    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit(
            f"Reference propeller '{config.reference_propeller_id}' not found in database."
        )

    rows = compare_fixed_vs_foldable_sweep(config, prop_entry, THROTTLE_VALUES)
    written = write_comparison_csv(output_path, rows)

    print(f"Config : {config_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("Karşılaştırma:")
    header = (
        f"{'thr':>5} {'rpm':>7} {'D_fix':>7} {'D_fold':>7} "
        f"{'T_fix':>7} {'T_fold':>7} {'dT%':>7} {'theta':>7}"
    )
    print(header)
    for row in rows:
        print(
            f"{row.throttle:5.2f} {row.rpm:7.0f} {row.fixed_diameter_m:7.4f} "
            f"{row.foldable_effective_diameter_m:7.4f} {row.fixed_thrust_n:7.3f} "
            f"{row.foldable_thrust_n:7.3f} {row.thrust_difference_percent:7.2f} "
            f"{row.theta_deg:7.2f}"
        )


if __name__ == "__main__":
    main()
