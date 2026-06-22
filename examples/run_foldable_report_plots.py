"""Foldable tasarım varyantı rapor grafikleri örneği."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.plots import (  # noqa: E402
    FOLDABLE_REPORT_FIGURE_NAMES,
    FOLDABLE_REPORT_MARKDOWN_NAME,
    generate_foldable_report_figures,
)


def main() -> None:
    foldable_dir = PROJECT_ROOT / "outputs" / "foldable"
    sweep_path = foldable_dir / "design_variant_sweep.csv"
    summary_path = foldable_dir / "design_variant_summary.csv"
    decision_path = foldable_dir / "design_variant_decision_matrix.csv"
    figures_dir = foldable_dir / "figures"

    missing = [
        path
        for path in (sweep_path, summary_path, decision_path)
        if not path.is_file()
    ]
    if missing:
        missing_list = "\n".join(f"  - {path}" for path in missing)
        raise SystemExit(
            "Required CSV inputs are missing:\n"
            f"{missing_list}\n"
            "Run design variant sweep, summary, and decision matrix examples first."
        )

    written = generate_foldable_report_figures(
        sweep_csv_path=sweep_path,
        summary_csv_path=summary_path,
        decision_csv_path=decision_path,
        figures_dir=figures_dir,
    )

    print(f"Sweep   : {sweep_path}")
    print(f"Summary : {summary_path}")
    print(f"Decision: {decision_path}")
    print(f"Output  : {figures_dir}")
    print(f"Figures : {len(written) - 1}")
    for name in FOLDABLE_REPORT_FIGURE_NAMES:
        print(f"  - {name}")
    print(f"  - {FOLDABLE_REPORT_MARKDOWN_NAME}")


if __name__ == "__main__":
    main()
