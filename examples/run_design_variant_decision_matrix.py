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

    sweep_path = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_sweep.csv"
    rows = build_decision_matrix_from_csv(summary_path, sweep_csv_path=sweep_path)
    written = write_design_variant_decision_csv(output_path, rows)

    print(f"Input  : {summary_path}")
    print(f"Sweep  : {sweep_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("Karar matrisi:")
    header = (
        f"{'variant':>22} {'folded':>7} {'gain%':>7} "
        f"{'start':>6} {'flight':>6} {'deploy':>6} {'takeoff':>7} {'note':>22}"
    )
    print(header)
    for row in rows:
        print(
            f"{row.variant_id:>22} {row.folded_diameter_ratio:7.4f} "
            f"{row.compactness_gain_percent:7.2f} "
            f"{row.startup_thrust_score:6.3f} {row.flight_performance_score:6.3f} "
            f"{row.deployment_score:6.3f} {row.takeoff_transition_score:7.3f} "
            f"{row.recommendation_note:>22}"
        )


if __name__ == "__main__":
    main()
