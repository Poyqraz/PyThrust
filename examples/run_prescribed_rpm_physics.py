"""Run propeller-first prescribed-RPM physics simulation and export debug outputs."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    PrescribedRpmConfig,
    analyze_physics_stability,
    plot_physics_debug_figures,
    quasi_static_equilibrium_theta_deg,
    run_dt_sensitivity_cases,
    run_hinge_parameter_diagnostic_sweep,
    run_moment_geometry_diagnostic_cases,
    run_prescribed_rpm_physics,
    write_diagnostic_sweep_csv,
    write_moment_geometry_diagnostic_csv,
    write_physics_csv,
    write_stability_report,
)
from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "foldable" / "dynamics" / "physics"


def main() -> None:
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit("Reference propeller not found.")

    constant_sim = PrescribedRpmConfig(
        dt_s=0.001,
        t_end_s=2.0,
        rpm_mode="constant",
        constant_rpm=7100.0,
    )
    ramp_sim = PrescribedRpmConfig(
        dt_s=0.001,
        t_end_s=2.0,
        rpm_mode="ramp",
        ramp_rpm_end=7100.0,
        ramp_time_s=0.5,
    )

    constant_states = run_prescribed_rpm_physics(config, prop_entry, sim=constant_sim)
    ramp_states = run_prescribed_rpm_physics(config, prop_entry, sim=ramp_sim)

    csv_constant = write_physics_csv(
        OUTPUT_DIR / "prescribed_rpm_7100_constant.csv",
        constant_states,
    )
    csv_ramp = write_physics_csv(
        OUTPUT_DIR / "prescribed_rpm_ramp.csv",
        ramp_states,
    )
    figs_constant = plot_physics_debug_figures(
        constant_states,
        OUTPUT_DIR / "figures",
        prefix="constant_7100",
    )
    figs_ramp = plot_physics_debug_figures(
        ramp_states,
        OUTPUT_DIR / "figures",
        prefix="ramp",
    )

    eq_theta = quasi_static_equilibrium_theta_deg(7100.0, config)
    baseline = analyze_physics_stability(
        constant_states,
        config,
        case_id="constant_7100_dt0.001",
        rpm_profile="constant_7100",
        dt_s=0.001,
        notes=f"algebraic_equilibrium_theta_deg={eq_theta:.2f}" if eq_theta else "",
    )
    dt_cases = run_dt_sensitivity_cases(config, prop_entry)
    stability_rows = [baseline, *dt_cases]

    write_stability_report(
        str(OUTPUT_DIR / "prescribed_rpm_stability_report.csv"),
        stability_rows,
    )

    sweep_rows = run_hinge_parameter_diagnostic_sweep(config, prop_entry)
    write_diagnostic_sweep_csv(
        str(OUTPUT_DIR / "hinge_parameter_diagnostic_sweep.csv"),
        sweep_rows,
    )

    geometry_rows = run_moment_geometry_diagnostic_cases(config, prop_entry)
    write_moment_geometry_diagnostic_csv(
        str(OUTPUT_DIR / "hinge_moment_geometry_diagnostic.csv"),
        geometry_rows,
    )

    print(f"Config : {V02_CONFIG}")
    print(f"Constant CSV : {csv_constant} ({len(constant_states)} rows)")
    print(f"Ramp CSV     : {csv_ramp} ({len(ramp_states)} rows)")
    print(f"Figures      : {len(figs_constant) + len(figs_ramp)} PNGs under {OUTPUT_DIR / 'figures'}")
    print(f"Stability    : {OUTPUT_DIR / 'prescribed_rpm_stability_report.csv'}")
    print(f"Sweep        : {OUTPUT_DIR / 'hinge_parameter_diagnostic_sweep.csv'}")
    print(f"Geometry diag: {OUTPUT_DIR / 'hinge_moment_geometry_diagnostic.csv'}")
    if constant_states:
        last = constant_states[-1]
        print(
            f"Final constant: theta={last.theta_deg:.2f} deg, "
            f"T_root={last.thrust_root_n:.3f} N, T_tip={last.thrust_tip_n:.3f} N"
        )
    if eq_theta is not None:
        print(f"Algebraic equilibrium theta @ 7100 rpm: {eq_theta:.2f} deg")


if __name__ == "__main__":
    main()
