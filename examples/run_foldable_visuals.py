"""Generate foldable propeller 2D engineering schematics from CSV outputs."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.visualization.io import join_visual_states, state_for  # noqa: E402
from pythrust.foldable.visualization.panels import (  # noqa: E402
    DEFAULT_THROTTLE_SWEEP_VALUES,
    draw_throttle_sweep_panel,
    draw_variant_compare_panel,
)
from pythrust.foldable.visualization.schematic import draw_single_state  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "foldable" / "visuals"
SWEEP_CSV = PROJECT_ROOT / "outputs" / "foldable" / "design_variant_sweep.csv"
MOMENT_CSV = PROJECT_ROOT / "outputs" / "foldable" / "moment_kinematics_validation.csv"
PARAMS_CSV = PROJECT_ROOT / "outputs" / "foldable" / "variant_physical_parameters.csv"

DEFAULT_VARIANT_ID = "TIP_HINGED_250_RT75_25"
DEFAULT_SINGLE_THROTTLE = 0.6
DEFAULT_COMPARE_THROTTLE = 0.6
REPORT_NAME = "foldable_visuals_report.md"


def _require_csv(path: Path, script_hint: str) -> None:
    if not path.is_file():
        raise SystemExit(
            f"Missing CSV: {path}\n"
            f"Run {script_hint} first."
        )


def _write_report(
    output_dir: Path,
    *,
    written_files: list[Path],
    variant_id: str,
    single_throttle: float,
    compare_throttle: float,
) -> Path:
    report_path = output_dir / REPORT_NAME
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Foldable 2D Visuals Report",
        "",
        f"Generated: {timestamp}",
        "",
        "## Inputs",
        "",
        f"- Sweep: `{SWEEP_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Moment validation: `{MOMENT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Variant parameters: `{PARAMS_CSV.relative_to(PROJECT_ROOT)}`",
        "",
        "## Model notes",
        "",
        "- 2D side elevation schematic (V1); physics model unchanged",
        "- V1 moment model: hinge_radius_m is stored but not used in opening moment calculation.",
        "- active_window_diameter_growth_score measures observed diameter growth over sampled "
        "throttle values, not total stowed-to-open geometric deployment.",
        "",
        "## Figures",
        "",
    ]
    for path in written_files:
        lines.append(f"- `{path.name}`")
    lines.extend(
        [
            "",
            "## Defaults used",
            "",
            f"- Single state: `{variant_id}` @ throttle={single_throttle}",
            f"- Throttle sweep panel: `{variant_id}`",
            f"- Variant compare panel: throttle={compare_throttle}",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    _require_csv(SWEEP_CSV, "examples/run_design_variant_sweep.py")
    _require_csv(MOMENT_CSV, "examples/run_moment_kinematics_validation.py")
    _require_csv(PARAMS_CSV, "examples/run_moment_kinematics_validation.py")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    states = join_visual_states(
        SWEEP_CSV,
        MOMENT_CSV,
        PARAMS_CSV,
        throttle_values=list(DEFAULT_THROTTLE_SWEEP_VALUES),
    )

    single = state_for(states, DEFAULT_VARIANT_ID, DEFAULT_SINGLE_THROTTLE)
    written: list[Path] = []

    single_path = draw_single_state(
        single,
        output_path=OUTPUT_DIR / f"single_state_{DEFAULT_VARIANT_ID}_thr_{DEFAULT_SINGLE_THROTTLE:.1f}.png",
    )
    written.append(single_path)

    sweep_panel_path = draw_throttle_sweep_panel(
        DEFAULT_VARIANT_ID,
        states,
        output_path=OUTPUT_DIR / f"throttle_sweep_{DEFAULT_VARIANT_ID}.png",
    )
    written.append(sweep_panel_path)

    compare_panel_path = draw_variant_compare_panel(
        DEFAULT_COMPARE_THROTTLE,
        states,
        output_path=OUTPUT_DIR / f"variant_compare_thr_{DEFAULT_COMPARE_THROTTLE:.1f}.png",
    )
    written.append(compare_panel_path)

    report_path = _write_report(
        OUTPUT_DIR,
        written_files=written,
        variant_id=DEFAULT_VARIANT_ID,
        single_throttle=DEFAULT_SINGLE_THROTTLE,
        compare_throttle=DEFAULT_COMPARE_THROTTLE,
    )

    print(f"Sweep CSV   : {SWEEP_CSV}")
    print(f"Moment CSV  : {MOMENT_CSV}")
    print(f"Params CSV  : {PARAMS_CSV}")
    print(f"Output dir  : {OUTPUT_DIR}")
    print(f"Figures     : {len(written)}")
    for path in written:
        print(f"  - {path.name}")
    print(f"Report      : {report_path.name}")


if __name__ == "__main__":
    main()
