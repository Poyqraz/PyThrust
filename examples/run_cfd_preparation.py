"""Generate foldable V2 CFD preparation exports (input data only — not CFD results)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pythrust.foldable.dynamics.cfd_preparation import (  # noqa: E402
    CFD_PREP_OUTPUT_DIR,
    CFD_STATUS_NOTE,
    run_cfd_preparation_v2,
)
from pythrust.foldable.models import load_config  # noqa: E402
from pythrust.propellers import PropellerDatabase  # noqa: E402

V02_CONFIG = PROJECT_ROOT / "configs" / "foldable" / "TIP_HINGED_250_V02.json"
OUTPUT_DIR = PROJECT_ROOT / CFD_PREP_OUTPUT_DIR


def main() -> None:
    config = load_config(V02_CONFIG)
    db = PropellerDatabase()
    db.load(PROJECT_ROOT / "data" / "propellers" / "apc_202602", strict=False)
    prop_entry = db.get(config.reference_propeller_id)
    if prop_entry is None:
        raise SystemExit("Reference propeller not found.")

    paths = run_cfd_preparation_v2(config, prop_entry, output_dir=OUTPUT_DIR)
    print(f"Status   : {CFD_STATUS_NOTE}")
    print(f"Output   : {OUTPUT_DIR}")
    for name, path in paths.items():
        print(f"  - {name}: {path.name}")


if __name__ == "__main__":
    main()
