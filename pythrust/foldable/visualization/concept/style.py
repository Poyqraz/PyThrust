"""Visual constants for concept/report schematics."""

from __future__ import annotations

FACE_BLACK = "black"
EDGE_BLACK = "black"
BG_WHITE = "white"
LABEL_COLOR = "0.15"
ARROW_COLOR = "0.2"

BLADE_WIDTH_FRACTION = 0.06
MOTOR_OUTER_RADIUS_FRACTION = 0.055
MOTOR_INNER_RADIUS_FRACTION = 0.02
HINGE_MARKER_RADIUS_FRACTION = 0.018

STATIC_FIGSIZE = (8.0, 5.5)
STATE_FIGSIZE = (7.5, 5.5)
PANEL_SWEEP_FIGSIZE = (12.0, 8.0)
PANEL_COMPARE_FIGSIZE = (16.0, 4.5)

FIGURE_DPI = 150
LABEL_FONTSIZE = 9
INFO_FONTSIZE = 7
PANEL_TITLE_FONTSIZE = 9
SUBPLOT_LABEL_FONTSIZE = 7

ARROW_STYLE = "-|>"
ARROW_LINEWIDTH = 0.9

# Concept deployment display angles (visualization only; not model physics).
# Folded: secondary blade parallel to main blade, pointing toward hub (-x).
# Open: secondary blade extends radially outward (+x).
CONCEPT_FOLDED_DISPLAY_ANGLE_DEG = 180.0
CONCEPT_OPEN_DISPLAY_ANGLE_DEG = 0.0
DEPLOYMENT_SEQUENCE_DURATION_S = 2.0
DEFAULT_DEPLOYMENT_PROGRESS_STEPS: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

SEQUENCE_FIGSIZE = (12.0, 4.5)

CONCEPT_MODEL_NOTE = (
    "Concept deployment schematic (folded-start interpretation); "
    "not CAD, not CFD, illustrative blade width."
)
