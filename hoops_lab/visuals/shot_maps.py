"""Shot scatter maps on the half court (player- and team-level).

Pure matplotlib figures, compatible with ``st.pyplot`` and report exports.
Empty frames degrade to an annotated empty court; missing coordinate columns
raise a clear ``ValueError``.
"""

from __future__ import annotations

import pandas as pd
from matplotlib.figure import Figure

from hoops_lab.visuals.court import draw_court

MADE_COLOR = "#16c47f"
MISS_COLOR = "#e0262c"
TEXT_MUTED = "#9ca3af"


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")


def _empty_court(title: str | None) -> Figure:
    fig, ax = draw_court()
    ax.text(0, 200, "No shots to plot", ha="center", color=TEXT_MUTED, fontsize=11)
    if title:
        ax.set_title(title, color=TEXT_MUTED)
    return fig


def player_shot_map(
    shots_df: pd.DataFrame,
    title: str | None = None,
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
    point_size: float = 18.0,
) -> Figure:
    """Made/missed scatter for one player (or any pre-filtered shot frame).

    Args:
        shots_df: One row per shot.
        title: Optional title (player name).
        x_col: X coordinate column (tenths of feet).
        y_col: Y coordinate column.
        made_col: 0/1 make flag; when absent all shots draw in one color.
        point_size: Marker size.

    Returns:
        A matplotlib Figure (annotated empty court for an empty frame).

    Raises:
        ValueError: If a coordinate column is missing.
    """
    _require(shots_df, [x_col, y_col])
    if shots_df.empty:
        return _empty_court(title)

    fig, ax = draw_court()
    if made_col in shots_df.columns:
        made = shots_df[shots_df[made_col] == 1]
        miss = shots_df[shots_df[made_col] == 0]
        ax.scatter(
            miss[x_col],
            miss[y_col],
            s=point_size,
            marker="x",
            c=MISS_COLOR,
            alpha=0.55,
            linewidths=1.0,
            label="missed",
        )
        ax.scatter(
            made[x_col],
            made[y_col],
            s=point_size,
            c=MADE_COLOR,
            alpha=0.75,
            edgecolors="none",
            label="made",
        )
        legend = ax.legend(loc="upper right", frameon=False, fontsize=8)
        for text in legend.get_texts():
            text.set_color(TEXT_MUTED)
    else:
        ax.scatter(
            shots_df[x_col],
            shots_df[y_col],
            s=point_size,
            c=MADE_COLOR,
            alpha=0.7,
            edgecolors="none",
        )
    if title:
        ax.set_title(title, color="#f1f5f9")
    return fig


def team_shot_map(
    shots_df: pd.DataFrame,
    title: str | None = None,
    x_col: str = "LOC_X",
    y_col: str = "LOC_Y",
    made_col: str = "SHOT_MADE_FLAG",
    max_points: int = 4000,
    random_state: int = 42,
) -> Figure:
    """Team-aggregated shot scatter, deterministically subsampled when huge.

    Args:
        shots_df: All shots of a team (one or more seasons pooled upstream
            by ``build_team_window_profile``-style selection).
        title: Optional title.
        x_col: X coordinate column.
        y_col: Y coordinate column.
        made_col: 0/1 make flag.
        max_points: Plot at most this many shots (seeded sample keeps the
            figure readable and the output reproducible).
        random_state: Sampling seed.

    Returns:
        A matplotlib Figure.

    Raises:
        ValueError: If a coordinate column is missing.
    """
    _require(shots_df, [x_col, y_col])
    plot_df = shots_df
    if len(plot_df) > max_points:
        plot_df = plot_df.sample(n=max_points, random_state=random_state).sort_index()
    return player_shot_map(
        plot_df, title=title, x_col=x_col, y_col=y_col, made_col=made_col, point_size=8.0
    )
