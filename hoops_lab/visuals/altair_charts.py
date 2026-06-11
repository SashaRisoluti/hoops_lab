"""Reusable Altair chart blocks (dark broadcast styling).

Each builder accepts an already-prepared DataFrame and returns an
``alt.Chart`` — no database access, no network, no Streamlit. The dashboard
renders them with ``st.altair_chart``; reports can serialize them via
``chart.to_dict()``. Colors mirror the design tokens in
``dashboard/components/theme.py`` (tricolor data language: orange = good,
blue = mid, red = weak).
"""

from __future__ import annotations

import altair as alt
import pandas as pd

# Mirrors of the dashboard design tokens (hoops_lab must not import from
# dashboard/, so the shared values are restated here).
BG_CARD = "#14171D"
GRID = "#222834"
TEXT = "#EDEFF3"
TEXT_MUTED = "#8B93A3"
ORANGE = "#F0703A"
BLUE = "#2E5FB7"
RED = "#D2243C"

#: Tricolor scale for percentile-driven encodings.
TRICOLOR_DOMAIN = ["good", "mid", "weak"]
TRICOLOR_RANGE = [ORANGE, BLUE, RED]


def _require(data: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in data.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")


def _dark(chart: alt.Chart) -> alt.Chart:
    """Apply the shared dark styling to a chart."""
    return (
        chart.configure(background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            gridColor=GRID,
            domainColor=GRID,
            tickColor=GRID,
            labelColor=TEXT_MUTED,
            titleColor=TEXT_MUTED,
        )
        .configure_legend(labelColor=TEXT_MUTED, titleColor=TEXT_MUTED)
        .configure_title(color=TEXT)
    )


def build_four_factors_chart(data: pd.DataFrame, title: str = "Four Factors") -> alt.Chart:
    """Grouped bar chart comparing Four Factors between two sides.

    Args:
        data: Long-form frame with ``factor`` (eFG%, TOV%, OREB%, FTr),
            ``side`` (e.g. team name vs "Opponent") and ``value``.
        title: Chart title.

    Returns:
        A serializable ``alt.Chart``.
    """
    _require(data, ["factor", "side", "value"])
    chart = (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X("side:N", title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y("value:Q", title=None),
            color=alt.Color("side:N", scale=alt.Scale(range=[ORANGE, BLUE]), title=None),
            column=alt.Column("factor:N", title=None, sort=["eFG%", "TOV%", "OREB%", "FTr"]),
            tooltip=["factor", "side", alt.Tooltip("value:Q", format=".3f")],
        )
        .properties(width=90, height=160)
    )
    return _dark(chart)


def build_team_percentile_chart(data: pd.DataFrame, title: str = "League percentiles") -> alt.Chart:
    """Horizontal percentile bars with the tricolor data language.

    Args:
        data: One row per metric with ``metric`` and ``percentile`` (0-100).
        title: Chart title.

    Returns:
        A serializable ``alt.Chart`` (orange >= 66, blue 33-66, red < 33).
    """
    _require(data, ["metric", "percentile"])
    band = data.assign(
        band=pd.cut(
            data["percentile"],
            bins=[-0.1, 33, 66, 100.1],
            labels=["weak", "mid", "good"],
        ).astype(str)
    )
    chart = (
        alt.Chart(band, title=title)
        .mark_bar(height=14)
        .encode(
            x=alt.X("percentile:Q", scale=alt.Scale(domain=[0, 100]), title="percentile"),
            y=alt.Y("metric:N", sort="-x", title=None),
            color=alt.Color(
                "band:N",
                scale=alt.Scale(domain=TRICOLOR_DOMAIN, range=TRICOLOR_RANGE),
                legend=None,
            ),
            tooltip=["metric", alt.Tooltip("percentile:Q", format=".0f")],
        )
        .properties(height=alt.Step(24))
    )
    return _dark(chart)


def build_recent_form_chart(
    data: pd.DataFrame,
    title: str = "Recent form",
    x_col: str = "game",
    y_col: str = "value",
) -> alt.Chart:
    """Line chart of a rolling rating over recent games.

    Args:
        data: One row per game with ``x_col`` (game index/date) and
            ``y_col`` (rolling NET/OFF/DEF rating).
        title: Chart title.
        x_col: X column name.
        y_col: Y column name.

    Returns:
        A serializable ``alt.Chart``.
    """
    _require(data, [x_col, y_col])
    chart = (
        alt.Chart(data, title=title)
        .mark_line(color=ORANGE, point=alt.OverlayMarkDef(color=ORANGE, size=24))
        .encode(
            x=alt.X(f"{x_col}:Q", title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, alt.Tooltip(f"{y_col}:Q", format=".2f")],
        )
        .properties(height=180)
    )
    return _dark(chart)


def build_shot_profile_chart(data: pd.DataFrame, title: str = "Shot profile") -> alt.Chart:
    """Zone volume bars, colored by efficiency when available.

    Args:
        data: One row per zone with ``zone``, ``frequency`` (0-1 share) and
            optionally ``fg_pct``.
        title: Chart title.

    Returns:
        A serializable ``alt.Chart``.
    """
    _require(data, ["zone", "frequency"])
    has_eff = "fg_pct" in data.columns
    tooltip = ["zone", alt.Tooltip("frequency:Q", format=".1%")]
    if has_eff:
        tooltip.append(alt.Tooltip("fg_pct:Q", format=".1%"))
    chart = (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X("frequency:Q", axis=alt.Axis(format=".0%"), title="volume share"),
            y=alt.Y("zone:N", sort=None, title=None),
            color=(
                alt.Color(
                    "fg_pct:Q",
                    scale=alt.Scale(range=[RED, BLUE, ORANGE]),
                    title="FG%",
                    legend=alt.Legend(format=".0%"),
                )
                if has_eff
                else alt.value(BLUE)
            ),
            tooltip=tooltip,
        )
        .properties(height=alt.Step(26))
    )
    return _dark(chart)


def build_cluster_distribution_chart(
    data: pd.DataFrame, title: str = "Players per archetype"
) -> alt.Chart:
    """Bar chart of player counts per archetype/cluster.

    Args:
        data: One row per archetype with ``label`` and ``players`` count.
        title: Chart title.

    Returns:
        A serializable ``alt.Chart``.
    """
    _require(data, ["label", "players"])
    chart = (
        alt.Chart(data, title=title)
        .mark_bar(color=ORANGE)
        .encode(
            x=alt.X("players:Q", title="players"),
            y=alt.Y("label:N", sort="-x", title=None),
            tooltip=["label", "players"],
        )
        .properties(height=alt.Step(24))
    )
    return _dark(chart)


def build_som_map_chart(
    coords: pd.DataFrame,
    grid_size: tuple[int, int],
    color_col: str = "archetype",
    highlight_team_id: int | None = None,
    highlight_player_id: int | None = None,
    title: str = "SOM similarity map",
) -> alt.Chart:
    """Topological SOM scatter: nearby players have similar shot profiles.

    Args:
        coords: Output of ``assign_som_coordinates`` with ``som_x``/``som_y``
            plus player metadata; ``color_col`` (e.g. the KMeans archetype
            label) drives the overlay color when present.
        grid_size: (width, height) of the SOM grid (sets the axis domains).
        highlight_team_id: Players of this team render larger with a ring.
        highlight_player_id: One player to single out (diamond marker).
        title: Chart title.

    Returns:
        A serializable ``alt.Chart``. Players sharing a cell are spread with
        a small deterministic jitter so every point stays visible.
    """
    _require(coords, ["som_x", "som_y"])
    data = coords.copy().reset_index(drop=True)

    # Deterministic in-cell jitter: spread co-located players on a 3x3 micro-grid.
    rank = data.groupby(["som_x", "som_y"]).cumcount()
    data["som_x_jitter"] = data["som_x"] + (rank % 3 - 1) * 0.22
    data["som_y_jitter"] = data["som_y"] + (rank // 3 % 3 - 1) * 0.22

    data["highlighted"] = False
    if highlight_team_id is not None and "team_id" in data.columns:
        data["highlighted"] = data["team_id"] == highlight_team_id
    data["is_selected_player"] = False
    if highlight_player_id is not None and "player_id" in data.columns:
        data["is_selected_player"] = data["player_id"] == highlight_player_id

    tooltip = [
        c
        for c in ("player_name", "team_name", color_col, "kmeans_cluster", "total_attempts")
        if c in data.columns
    ]
    color = (
        alt.Color(f"{color_col}:N", title="archetype")
        if color_col in data.columns
        else alt.value(BLUE)
    )
    chart = (
        alt.Chart(data, title=title)
        .mark_point(filled=True)
        .encode(
            x=alt.X(
                "som_x_jitter:Q",
                title=None,
                scale=alt.Scale(domain=[-0.5, grid_size[0] - 0.5]),
                axis=alt.Axis(grid=True, labels=False, ticks=False, tickCount=grid_size[0]),
            ),
            y=alt.Y(
                "som_y_jitter:Q",
                title=None,
                scale=alt.Scale(domain=[-0.5, grid_size[1] - 0.5]),
                axis=alt.Axis(grid=True, labels=False, ticks=False, tickCount=grid_size[1]),
            ),
            color=color,
            size=alt.condition(alt.datum.highlighted, alt.value(160), alt.value(45)),
            stroke=alt.condition(alt.datum.highlighted, alt.value(TEXT), alt.value(None)),
            shape=alt.condition(
                alt.datum.is_selected_player, alt.value("diamond"), alt.value("circle")
            ),
            opacity=alt.condition(alt.datum.highlighted, alt.value(1.0), alt.value(0.65)),
            tooltip=tooltip,
        )
        .properties(height=420)
    )
    return _dark(chart)


def build_centroid_profile_chart(
    data: pd.DataFrame, title: str = "Centroid profiles (z-scores vs league mean)"
) -> alt.Chart:
    """Faceted bars comparing KMeans centroids feature by feature.

    Args:
        data: Long-form frame with ``label`` (archetype), ``feature`` and
            ``value`` (centroid z-score vs the league mean).
        title: Chart title.

    Returns:
        A serializable ``alt.Chart`` (positive z orange, negative red).
    """
    _require(data, ["label", "feature", "value"])
    chart = (
        alt.Chart(data, title=title)
        .mark_bar()
        .encode(
            x=alt.X("value:Q", title="z-score"),
            y=alt.Y("feature:N", sort=None, title=None),
            color=alt.condition(alt.datum.value > 0, alt.value(ORANGE), alt.value(RED)),
            row=alt.Row("label:N", title=None, header=alt.Header(labelColor=TEXT)),
            tooltip=["label", "feature", alt.Tooltip("value:Q", format="+.2f")],
        )
        .properties(height=alt.Step(16))
    )
    return _dark(chart)
