#!/usr/bin/env bash
# Build a standalone PyFoldable repository from PyThrust foldable work.
set -euo pipefail

SRC="/workspace"
DEST="${1:-/tmp/pyfoldable-standalone}"

rm -rf "$DEST"
mkdir -p "$DEST"

# Core package (renamed from pythrust.foldable)
cp -a "$SRC/pythrust/foldable" "$DEST/pyfoldable"

# Minimal vendored PyThrust slices for propeller + propulsion coupling
mkdir -p "$DEST/pythrust/propellers" "$DEST/pythrust/propulsion"
cp "$SRC/pythrust/__init__.py" "$DEST/pythrust/"
cp "$SRC/pythrust/propellers/__init__.py" "$DEST/pythrust/propellers/"
cp "$SRC/pythrust/propellers/database.py" "$DEST/pythrust/propellers/"
cp "$SRC/pythrust/propulsion/models.py" "$DEST/pythrust/propulsion/"
cp "$SRC/pythrust/propulsion/solver.py" "$DEST/pythrust/propulsion/"
cat > "$DEST/pythrust/propulsion/__init__.py" <<'PYTHRUST_PROP_INIT'
"""Minimal propulsion exports for PyFoldable operating-point coupling."""

from .models import (  # noqa: F401
    BatterySpec,
    MotorSpec,
    OperatingPoint,
    PropellerSpec,
    SystemSpec,
)
from .solver import PropulsionSolver, SolverConfig  # noqa: F401
PYTHRUST_PROP_INIT

# Config, docs, data, examples, tests, reports
mkdir -p "$DEST/configs/foldable" "$DEST/docs/superpowers/specs" "$DEST/data/propellers/apc_202602"
cp "$SRC/configs/foldable/"*.json "$DEST/configs/foldable/"
cp "$SRC/docs/foldable_conventions.md" "$DEST/docs/"
cp "$SRC/docs/superpowers/specs/v2_"*.md "$DEST/docs/superpowers/specs/" 2>/dev/null || true
cp "$SRC/data/propellers/apc_202602/APC_10x4.7SF."* "$DEST/data/propellers/apc_202602/"
cp -a "$SRC/tests/foldable" "$DEST/tests"
cp -a "$SRC/reports/foldable_v2_engineering_design" "$DEST/reports/foldable_v2_engineering_design"
cp "$SRC/LICENSE" "$DEST/"

FOLDABLE_EXAMPLES=(
  run_cfd_preparation.py
  generate_foldable_engineering_report.py
  run_deployment_diagnostics.py
  run_prescribed_rpm_physics.py
  run_dynamic_spinup.py
  run_foldable_visuals.py
  run_design_variant_decision_matrix.py
  run_moment_kinematics_validation.py
  run_foldable_report_plots.py
  run_design_variant_summary.py
  run_design_variant_sweep.py
  run_fixed_vs_foldable_comparison.py
  run_foldable_operating_point.py
  run_foldable_sweep.py
)
mkdir -p "$DEST/examples"
for ex in "${FOLDABLE_EXAMPLES[@]}"; do
  cp "$SRC/examples/$ex" "$DEST/examples/"
done

# Rewrite imports: pythrust.foldable -> pyfoldable
find "$DEST" -name '*.py' -print0 | while IFS= read -r -d '' file; do
  sed -i 's/pythrust\.foldable/pyfoldable/g' "$file"
done

# Fix PROJECT_ROOT depth: tests/ layout is one level shallower than tests/foldable/
find "$DEST/tests/dynamics" -name '*.py' -print0 | while IFS= read -r -d '' file; do
  sed -i 's/\.parents\[3\]/\.parents[2]/g' "$file"
done
find "$DEST/tests" -maxdepth 1 -name 'test_*.py' -print0 | while IFS= read -r -d '' file; do
  sed -i 's/\.parents\[2\]/\.parents[1]/g' "$file"
done

# Package version marker (keep original __init__ exports)
python3 - "$DEST/pyfoldable/__init__.py" <<'PY'
import sys
from pathlib import Path
init = Path(sys.argv[1])
text = init.read_text()
if "__version__" not in text:
    end = text.index('"""', text.index('"""') + 3) + 3 if text.startswith('"""') else 0
    text = text[:end] + '\n\n__version__ = "0.2.0"' + text[end:]
    init.write_text(text)
PY

cat > "$DEST/pyproject.toml" <<'PYPROJECT'
[build-system]
requires = ["setuptools>=61.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyfoldable"
version = "0.2.0"
description = "Tip-hinged foldable propeller analysis for UAV electric propulsion ."
readme = "README.md"
authors = [{ name = "Hüseyin Karakaya" }]
license = { text = "Apache-2.0" }
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.20",
    "scipy>=1.7",
]

[project.optional-dependencies]
plot = ["matplotlib>=3.4"]
dev = ["pytest>=7.0"]

[tool.setuptools.packages.find]
where = ["."]
include = ["pyfoldable*", "pythrust*"]
PYPROJECT

cat > "$DEST/.gitignore" <<'GITIGNORE'
*.pyc
__pycache__/
venv/
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
outputs/
scratch/
GITIGNORE

cat > "$DEST/README.md" <<'README'
# PyFoldable

Standalone export of the foldable propeller analysis stack from [PyThrust](https://github.com/Poyqraz/PyThrust) .

## Scope

- V1 kinematics, effective diameter, design sweeps, decision matrix
- V2 hinge dynamics, split thrust, motor-coupled performance
- Engineering design report + Level-1 CFD preparation exports
- Minimal vendored `pythrust.propellers` + `pythrust.propulsion` for operating-point coupling

**Not included:** PyThrust core changes, OpenMDAO, full propeller database, CFD solver runs.

## Install

```bash
pip install -e ".[dev,plot]"
```

## Quick start

```bash
python3 examples/run_foldable_sweep.py
python3 examples/generate_foldable_engineering_report.py
python3 examples/run_cfd_preparation.py
```

## Tests

```bash
pytest tests/ -q
```

## Key results @ 7100 rpm (model)

| Metric | Value |
|--------|-------|
| root_only_20cm | ~3.73 N |
| foldable pretest | ~6.37 N |
| fixed 25cm reference | ~9.10 N |
| gain vs compact root | ~+70.9% |

See `reports/foldable_v2_engineering_design/` for the full engineering report.

## License

Apache-2.0 (see LICENSE).
README

echo "Built standalone PyFoldable at $DEST"
