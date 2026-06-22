"""Tasarım varyantı sweep özet metrikleri örneği.

``design_variant_sweep.csv`` dosyasından varyant başına kompaktlık ve itki
özetini üretir.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.summary import (  # noqa: E402
    summarize_design_variants_from_csv,
    write_design_variant_summary_csv,
)


def main() -> None:
    sweep_path = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_sweep.csv"
    output_path = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_summary.csv"

    if not sweep_path.is_file():
        raise SystemExit(
            f"Sweep CSV not found: {sweep_path}\n"
            "Run examples/run_design_variant_sweep.py first."
        )

    rows = summarize_design_variants_from_csv(sweep_path)
    written = write_design_variant_summary_csv(output_path, rows)

    print(f"Input  : {sweep_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("Özet (tüm varyantlar):")
    header = (
        f"{'variant':>22} {'root':>4} {'tip':>4} {'folded':>7} "
        f"{'gain%':>7} {'dT@0.2':>8} {'dT@1.0':>8} {'score':>8}"
    )
    print(header)
    for row in rows:
        print(
            f"{row.variant_id:>22} {row.root_ratio:4d} {row.tip_ratio:4d} "
            f"{row.folded_diameter_ratio:7.4f} {row.compactness_gain_percent:7.2f} "
            f"{row.thrust_diff_at_02:8.2f} {row.thrust_diff_at_10:8.2f} "
            f"{row.score_simple:8.2f}"
        )


if __name__ == "__main__":
    main()
