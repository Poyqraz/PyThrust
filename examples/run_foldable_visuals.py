"""Generate foldable propeller 2D engineering schematics from CSV outputs."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.foldable.visualization.io import join_visual_states, state_for  # noqa: E402
from pythrust.foldable.visualization.concept.frames import export_deployment_frames  # noqa: E402
from pythrust.foldable.visualization.concept.panels import (  # noqa: E402
    draw_throttle_sweep_concept,
    draw_variant_compare_concept,
)
from pythrust.foldable.visualization.concept.schematic import (  # noqa: E402
    draw_single_state_concept,
    draw_static_overview,
)
from pythrust.foldable.visualization.concept.sequence import draw_deployment_sequence  # noqa: E402
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
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
DEFAULT_SINGLE_THROTTLE = 0.6
DEFAULT_COMPARE_THROTTLE = 0.6
REPORT_NAME = "foldable_2d_visuals_report.md"


def _require_csv(path: Path, script_hint: str) -> None:
    if not path.is_file():
        raise SystemExit(
            f"Missing CSV: {path}\n"
            f"Run {script_hint} first."
        )


def _write_report(
    output_dir: Path,
    *,
    radial_files: list[Path],
    concept_files: list[Path],
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
        "- Physics model unchanged.",
        "- D_eff is aerodynamic effective diameter during flight startup.",
        "- `stowed_envelope_diameter_m` is only the proposal storage envelope visualization target.",
        "- Ground mode thrust is not analyzed.",
        "- V1 moment model: hinge_radius_m is stored but not used in opening moment calculation.",
        "- active_window_diameter_growth_score measures observed diameter growth over sampled "
        "throttle values, not total stowed-to-open geometric deployment.",
        "",
        "## 1. Existing radial/effective-diameter visualizations",
        "",
        "Line-based engineering schematics for effective-diameter analysis and validation.",
        "",
    ]
    for path in radial_files:
        lines.append(f"- `{path.name}` — radial schematic with D_eff / open / stowed reference circles")
    lines.extend(
        [
            "",
            "## 2. Concept deployment schematic visualizations",
            "",
            "Presentation/mechanical explanation visuals with folded-start interpretation.",
            "Secondary blade uses visualization-only `display_hinge_angle_deg` (folded=180°, "
            "open=0°), mapped from model `theta_deg` via `deployment_progress_01`.",
            "Static overview shows the near-folded initial configuration.",
            "",
        ]
    )
    concept_captions = {
        "concept_static_overview.png": "static component overview with bilingual labels",
        "concept_state_TIP_HINGED_250_RT75_25_thr_0.6.png": (
            f"single-state concept schematic for `{variant_id}` @ throttle={single_throttle}"
        ),
        "concept_throttle_sweep_TIP_HINGED_250_RT75_25.png": (
            f"concept throttle sweep for `{variant_id}`"
        ),
        "concept_variant_compare_thr_0.6.png": (
            f"concept variant comparison at throttle={compare_throttle}"
        ),
        "concept_deployment_sequence_TIP_HINGED_250_RT75_25.png": (
            f"deployment sequence (folded → open) for `{variant_id}`"
        ),
    }
    for path in concept_files:
        caption = concept_captions.get(path.name, "concept schematic")
        lines.append(f"- `{path.name}` — {caption}")
    lines.extend(
        [
            "",
            "## 3. Radial vs concept visualization",
            "",
            "| Aspect | Radial / effective-diameter (analysis) | Concept deployment (presentation) |",
            "|---|---|---|",
            "| Purpose | Model interpretation and performance analysis | Mechanical folding/deployment explanation |",
            "| Secondary blade angle | Model `theta_deg` (0° = radial open) | `display_hinge_angle_deg` (180° = folded parallel) |",
            "| Start state | Uses model angle directly | Folded/near-folded parallel to main blade |",
            "| Style | Line-based with measurement circles | Black filled blade shapes |",
            "| D_eff overlay | Yes | No (values in info box only) |",
            "| Stowed envelope circle | Yes (when configured) | No |",
            "| Component labels | Engineering annotations | Bilingual arrows (static overview) |",
            "",
            "## 4. Limitations",
            "",
            "- Not CAD.",
            "- Not CFD.",
            "- Not true airfoil geometry.",
            "- V1 schematic only; blade width and motor connection are illustrative.",
            "- Concept deployment schematic uses folded-start interpretation; radial visuals "
            "remain the primary tool for effective-diameter analysis.",
            "- Frame export under `concept/frames/<variant_id>/deployment/` for future animation.",
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

    config = load_config(DEFAULT_CONFIG_PATH)
    diameter_open_m = config.geometry.diameter_open_m
    stowed_envelope_diameter_m = config.geometry.stowed_envelope_diameter_m
    theta_min_deg = config.hinge.theta_min_deg
    blade_count = config.geometry.blade_count

    states = join_visual_states(
        SWEEP_CSV,
        MOMENT_CSV,
        PARAMS_CSV,
        throttle_values=list(DEFAULT_THROTTLE_SWEEP_VALUES),
        diameter_open_m=diameter_open_m,
        stowed_envelope_diameter_m=stowed_envelope_diameter_m,
        theta_min_deg=theta_min_deg,
        blade_count=blade_count,
    )

    single = state_for(states, DEFAULT_VARIANT_ID, DEFAULT_SINGLE_THROTTLE)
    radial_written: list[Path] = []
    concept_written: list[Path] = []

    single_path = draw_single_state(
        single,
        output_path=OUTPUT_DIR / f"single_state_{DEFAULT_VARIANT_ID}_thr_{DEFAULT_SINGLE_THROTTLE:.1f}.png",
    )
    radial_written.append(single_path)

    sweep_panel_path = draw_throttle_sweep_panel(
        DEFAULT_VARIANT_ID,
        states,
        output_path=OUTPUT_DIR / f"throttle_sweep_{DEFAULT_VARIANT_ID}.png",
    )
    radial_written.append(sweep_panel_path)

    compare_panel_path = draw_variant_compare_panel(
        DEFAULT_COMPARE_THROTTLE,
        states,
        output_path=OUTPUT_DIR / f"variant_compare_thr_{DEFAULT_COMPARE_THROTTLE:.1f}.png",
    )
    radial_written.append(compare_panel_path)

    concept_written.append(
        draw_static_overview(output_path=OUTPUT_DIR / "concept_static_overview.png")
    )
    concept_written.append(
        draw_single_state_concept(
            single,
            output_path=OUTPUT_DIR
            / f"concept_state_{DEFAULT_VARIANT_ID}_thr_{DEFAULT_SINGLE_THROTTLE:.1f}.png",
        )
    )
    concept_written.append(
        draw_throttle_sweep_concept(
            DEFAULT_VARIANT_ID,
            states,
            output_path=OUTPUT_DIR / f"concept_throttle_sweep_{DEFAULT_VARIANT_ID}.png",
        )
    )
    concept_written.append(
        draw_variant_compare_concept(
            DEFAULT_COMPARE_THROTTLE,
            states,
            output_path=OUTPUT_DIR / f"concept_variant_compare_thr_{DEFAULT_COMPARE_THROTTLE:.1f}.png",
        )
    )
    concept_written.append(
        draw_deployment_sequence(
            single,
            output_path=OUTPUT_DIR / f"concept_deployment_sequence_{DEFAULT_VARIANT_ID}.png",
        )
    )
    export_deployment_frames(
        single,
        OUTPUT_DIR / "concept" / "frames",
    )

    report_path = _write_report(
        OUTPUT_DIR,
        radial_files=radial_written,
        concept_files=concept_written,
        variant_id=DEFAULT_VARIANT_ID,
        single_throttle=DEFAULT_SINGLE_THROTTLE,
        compare_throttle=DEFAULT_COMPARE_THROTTLE,
    )

    print(f"Sweep CSV   : {SWEEP_CSV}")
    print(f"Moment CSV  : {MOMENT_CSV}")
    print(f"Params CSV  : {PARAMS_CSV}")
    print(f"Output dir  : {OUTPUT_DIR}")
    print(f"Radial      : {len(radial_written)}")
    for path in radial_written:
        print(f"  - {path.name}")
    print(f"Concept     : {len(concept_written)}")
    for path in concept_written:
        print(f"  - {path.name}")
    print(f"Report      : {report_path.name}")


if __name__ == "__main__":
    main()
