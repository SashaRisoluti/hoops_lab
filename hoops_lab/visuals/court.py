"""Hand-drawn NBA half court in ShotChartDetail coordinates.

Pure matplotlib (the mplbasketball package pins numpy<2 and cannot be
installed alongside this stack, so the court is drawn from the official
dimensions instead). Units are tenths of feet with the hoop at the origin —
exactly the LOC_X/LOC_Y convention — so shot frames plot with no transform.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, Rectangle

from hoops_lab.features.shot_spatial_features import COURT_BOUNDS

#: Dark theme mirrors (see dashboard/components/theme.py).
COURT_BG = "#0f172a"
COURT_LINE = "#33415e"

_BASELINE_Y = -47.5  # baseline sits 4.75 ft behind the hoop center


def draw_court(
    ax: Axes | None = None,
    line_color: str = COURT_LINE,
    bg_color: str = COURT_BG,
    lw: float = 1.4,
) -> tuple[Figure, Axes]:
    """Draw an NBA half court ready for shot overlays.

    Args:
        ax: Existing axes to draw on; a new figure is created when None.
        line_color: Court line color.
        bg_color: Court/figure background color.
        lw: Line width.

    Returns:
        ``(figure, axes)`` with limits set to ``COURT_BOUNDS`` and equal
        aspect, compatible with ``st.pyplot``.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5.6))
    else:
        fig = ax.figure

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    common = {"color": line_color, "lw": lw, "fill": False}

    elements = [
        Circle((0, 0), radius=7.5, **common),  # hoop
        Rectangle((-30, -7.5 - 1), 60, 1, color=line_color, lw=lw, fill=True),  # backboard
        Rectangle((-80, _BASELINE_Y), 160, 190, **common),  # paint (outer box)
        Rectangle((-60, _BASELINE_Y), 120, 190, **common),  # paint (inner box)
        Arc((0, 142.5), 120, 120, theta1=0, theta2=180, color=line_color, lw=lw),  # FT top
        Arc(
            (0, 142.5),
            120,
            120,
            theta1=180,
            theta2=360,
            linestyle="dashed",
            color=line_color,
            lw=lw,
        ),
        Arc((0, 0), 80, 80, theta1=0, theta2=180, color=line_color, lw=lw),  # restricted
        Arc((0, 0), 475, 475, theta1=22, theta2=158, color=line_color, lw=lw),  # 3PT arc
        Arc((0, 422.5), 120, 120, theta1=180, theta2=360, color=line_color, lw=lw),  # center
    ]
    for element in elements:
        ax.add_patch(element)

    # Corner-three lines and boundaries.
    ax.plot([-220, -220], [_BASELINE_Y, 92.5], color=line_color, lw=lw)
    ax.plot([220, 220], [_BASELINE_Y, 92.5], color=line_color, lw=lw)
    ax.plot([-250, 250], [_BASELINE_Y, _BASELINE_Y], color=line_color, lw=lw)
    ax.plot([-250, -250], [_BASELINE_Y, 422.5], color=line_color, lw=lw)
    ax.plot([250, 250], [_BASELINE_Y, 422.5], color=line_color, lw=lw)
    ax.plot([-250, 250], [422.5, 422.5], color=line_color, lw=lw)

    x_min, x_max, y_min, y_max = COURT_BOUNDS
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax
