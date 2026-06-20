"""Run propeller-first prescribed-RPM physics simulation and export debug outputs."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics import (  # noqa: E402
    PrescribedRpmConfig,
    plot_physics_debug_figures,
    run_prescribed_rpm_physics,
    write_physics_csv,
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

    print(f"Config : {V02_CONFIG}")
    print(f"Constant CSV : {csv_constant} ({len(constant_states)} rows)")
    print(f"Ramp CSV     : {csv_ramp} ({len(ramp_states)} rows)")
    print(f"Figures      : {len(figs_constant) + len(figs_ramp)} PNGs under {OUTPUT_DIR / 'figures'}")
    if constant_states:
        last = constant_states[-1]
        print(f"Final constant: theta={last.theta_deg:.2f} deg, "
              f"T_root={last.thrust_root_n:.3f} N, T_tip={last.thrust_tip_n:.3f} N")


if __name__ == "__main__":
    main()
