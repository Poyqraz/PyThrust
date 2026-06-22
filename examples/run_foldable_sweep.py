"""Katlanabilir pervane RPM sweep örneği.

Örnek config dosyasını okuyarak belirli RPM aralığında performans tablosu üretir
ve ``outputs/foldable/sweep_results.csv`` dosyasına yazar.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Proje kökünü sys.path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable import (  # noqa: E402
    evaluate_sweep,
    load_config,
    write_sweep_csv,
)


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V01.json"
    output_path = PROJECT_ROOT / "outputs" / "foldable" / "sweep_results.csv"

    config = load_config(config_path)

    # Örnek RPM aralığı: 0 → 10000, 500 RPM adımlarla
    rpm_values = [float(rpm) for rpm in range(0, 10001, 500)]
    rows = evaluate_sweep(rpm_values, config)

    written = write_sweep_csv(output_path, rows)
    print(f"Config : {config_path}")
    print(f"Output : {written}")
    print(f"Rows   : {len(rows)}")
    print()
    print("İlk 5 satır:")
    print(f"{'rpm':>8} {'theta_deg':>10} {'D_eff_m':>10} {'thrust_N':>10}  model_note")
    for row in rows[:5]:
        print(
            f"{row.rpm:8.0f} {row.theta_deg:10.2f} "
            f"{row.effective_diameter_m:10.4f} {row.thrust_n:10.4f}  {row.model_note}"
        )


if __name__ == "__main__":
    main()
