"""Kök/uç oranı tasarım varyantı sweep örneği.

Farklı root/tip oranlarında (65/35 … 85/15) aynı açık çap (0.25 m) ve
throttle noktalarında sabit vs katlanabilir itki karşılaştırması üretir.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable import (  # noqa: E402
    load_config,
    sweep_design_variants,
    write_design_variant_sweep_csv,
)
from pythrust.propellers import PropellerDatabase  # noqa: E402

THROTTLE_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
    output_path = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_sweep.csv"

    config = load_config(config_path)

    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit(
            f"Reference propeller '{config.reference_propeller_id}' not found in database."
        )

    rows = sweep_design_variants(config, prop_entry, THROTTLE_VALUES)
    written = write_design_variant_sweep_csv(output_path, rows)

    print(f"Config : {config_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("İlk 5 satır:")
    header = (
        f"{'variant':>22} {'root':>4} {'tip':>4} {'thr':>5} "
        f"{'D_eff':>7} {'T_fix':>7} {'T_fold':>7} {'compact':>7}"
    )
    print(header)
    for row in rows[:5]:
        print(
            f"{row.variant_id:>22} {row.root_ratio:4d} {row.tip_ratio:4d} "
            f"{row.throttle:5.2f} {row.effective_diameter_m:7.4f} "
            f"{row.fixed_thrust_n:7.3f} {row.foldable_thrust_n:7.3f} "
            f"{row.compactness_ratio:7.4f}"
        )


if __name__ == "__main__":
    main()
