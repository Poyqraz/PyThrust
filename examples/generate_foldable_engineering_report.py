"""Generate foldable V2 engineering design report package (Markdown + CSV)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.engineering_design_report import (  # noqa: E402
    CONCLUSION_TR_NAME,
    FIGURE_INDEX_NAME,
    KEY_RESULTS_NAME,
    MAIN_REPORT_NAME,
    generate_foldable_v2_engineering_design_report,
)

INTERPOLATED_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "foldable"
    / "dynamics"
    / "physics"
    / "motor_coupled_7100rpm_interpolated_v2.csv"
)


def main() -> None:
    if not INTERPOLATED_CSV.is_file():
        raise SystemExit(
            f"Required input missing: {INTERPOLATED_CSV}\n"
            "Run examples/run_deployment_diagnostics.py first."
        )

    written = generate_foldable_v2_engineering_design_report(PROJECT_ROOT)
    report_dir = written[0].parent

    print(f"Input    : {INTERPOLATED_CSV}")
    print(f"Output   : {report_dir}")
    print(f"  - {MAIN_REPORT_NAME}")
    print(f"  - {KEY_RESULTS_NAME}")
    print(f"  - {FIGURE_INDEX_NAME}")
    print(f"  - model_assumptions_and_limits.md")
    print(f"  - {CONCLUSION_TR_NAME}")
    print(f"Files    : {len(written)}")


if __name__ == "__main__":
    main()
