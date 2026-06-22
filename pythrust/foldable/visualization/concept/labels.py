"""Arrow and bilingual label placement for static concept overview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from matplotlib.axes import Axes

from .deployment_frame import ConceptDeploymentFrame
from .geometry import blade_width_m, display_tip_point, hinge_point, motor_attachment
from .style import ARROW_COLOR, ARROW_LINEWIDTH, ARROW_STYLE, LABEL_COLOR, LABEL_FONTSIZE


@dataclass(frozen=True)
class ConceptLabel:
    """One arrow + bilingual label."""

    anchor: tuple[float, float]
    text_xy: tuple[float, float]
    text: str
    ha: str = "left"
    va: str = "center"


def static_overview_labels(frame: ConceptDeploymentFrame) -> List[ConceptLabel]:
    """Fixed label anchors for the static concept overview figure."""
    hinge_x, _ = hinge_point(frame)
    tip_x, tip_y = display_tip_point(frame)
    half_width = blade_width_m(frame) / 2.0
    outer_r, _ = motor_attachment(frame)

    main_mid_y = half_width * 1.6
    secondary_mid_x = (hinge_x + tip_x) / 2.0
    secondary_mid_y = tip_y / 2.0 + half_width * 0.5

    return [
        ConceptLabel(
            anchor=(hinge_x * 0.45, main_mid_y),
            text_xy=(0.02, 0.72),
            text="Main blade\nAna Kanat",
            ha="left",
            va="center",
        ),
        ConceptLabel(
            anchor=(secondary_mid_x, secondary_mid_y),
            text_xy=(0.58, 0.78),
            text="Secondary blade\nİkincil Kanat",
            ha="left",
            va="center",
        ),
        ConceptLabel(
            anchor=(hinge_x, half_width * 0.4),
            text_xy=(0.58, 0.42),
            text="Hinge\nEklem",
            ha="left",
            va="center",
        ),
        ConceptLabel(
            anchor=(0.0, outer_r[2] * 0.5),
            text_xy=(0.02, 0.18),
            text="Motor connection\nMotor Bağlantısı",
            ha="left",
            va="center",
        ),
    ]


def draw_static_labels(axis: Axes, frame: ConceptDeploymentFrame) -> None:
    """Draw bilingual arrows and labels on a concept axis."""
    for label in static_overview_labels(frame):
        axis.annotate(
            label.text,
            xy=label.anchor,
            xytext=label.text_xy,
            textcoords=axis.transAxes,
            arrowprops={
                "arrowstyle": ARROW_STYLE,
                "color": ARROW_COLOR,
                "lw": ARROW_LINEWIDTH,
            },
            fontsize=LABEL_FONTSIZE,
            color=LABEL_COLOR,
            ha=label.ha,
            va=label.va,
            linespacing=1.25,
            zorder=6,
        )
