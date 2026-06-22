"""Katlanabilir pervane operating point örneği (V2).

PyThrust solver ile denge RPM çözülür; foldable modül post-processing uygular.
Sonuçlar ``outputs/foldable/foldable_operating_point_results.csv`` dosyasına yazılır.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable import (  # noqa: E402
    evaluate_foldable_operating_point,
    load_config,
    write_operating_point_csv,
)
from pythrust.propellers import PropellerDatabase  # noqa: E402

THROTTLE_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
    output_path = PROJECT_ROOT / "outputs" / "foldable" / "foldable_operating_point_results.csv"

    config = load_config(config_path)

    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit(
            f"Reference propeller '{config.reference_propeller_id}' not found in database."
        )

    results = [
        evaluate_foldable_operating_point(config, prop_entry, throttle)
        for throttle in THROTTLE_VALUES
    ]

    written = write_operating_point_csv(output_path, results)
    print(f"Config : {config_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(results)}")
    print()
    print("Sonuçlar:")
    header = (
        f"{'throttle':>8} {'rpm':>8} {'theta':>8} {'D_eff':>8} "
        f"{'thrust':>8} {'current':>8} {'power':>8}"
    )
    print(header)
    for row in results:
        print(
            f"{row.throttle:8.2f} {row.rpm:8.0f} {row.theta_deg:8.2f} "
            f"{row.effective_diameter_m:8.4f} {row.thrust_n:8.3f} "
            f"{row.current_a:8.3f} {row.power_w:8.1f}"
        )


if __name__ == "__main__":
    main()
