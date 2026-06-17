"""Tasarım varyantı ağırlıklı karar matrisi örneği."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.decision import (  # noqa: E402
    build_decision_matrix_from_csv,
    write_design_variant_decision_csv,
)


def main() -> None:
    summary_path = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_summary.csv"
    output_path = (
        PROJECT_ROOT / "outputs" / "foldable" / "design_variant_decision_matrix.csv"
    )

    if not summary_path.is_file():
        raise SystemExit(
            f"Summary CSV not found: {summary_path}\n"
            "Run examples/run_design_variant_summary.py first."
        )

    rows = build_decision_matrix_from_csv(summary_path)
    written = write_design_variant_decision_csv(output_path, rows)

    print(f"Input  : {summary_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("Karar matrisi:")
    header = (
        f"{'variant':>22} {'gain%':>7} {'mean_dT':>8} "
        f"{'perf':>6} {'comp':>6} {'bal':>6} {'flt':>6} {'grd':>6} {'note':>18}"
    )
    print(header)
    for row in rows:
        print(
            f"{row.variant_id:>22} {row.compactness_gain_percent:7.2f} "
            f"{row.mean_thrust_difference_percent:8.2f} "
            f"{row.performance_score:6.3f} {row.compactness_score:6.3f} "
            f"{row.balanced_score:6.3f} {row.flight_priority_score:6.3f} "
            f"{row.ground_priority_score:6.3f} {row.recommendation_note:>18}"
        )


if __name__ == "__main__":
    main()
