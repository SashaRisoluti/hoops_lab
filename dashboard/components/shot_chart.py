"""Interactive shot chart on a half-court + zone efficiency aggregation."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.theme import COLOR_GOOD, COLOR_WEAK, COURT_LINE


def zone_efficiency(shots: pd.DataFrame) -> pd.DataFrame:
    """Aggregate attempts, FG% and points-per-shot by basic shot zone.

    Threes are worth 3 points (``SHOT_TYPE`` contains ``3PT``), everything
    else 2 — that is what makes PPS comparable across zones.
    """
    work = shots.copy()
    work["points"] = work["SHOT_MADE_FLAG"] * work["SHOT_TYPE"].str.contains("3PT").map(
        {True: 3, False: 2}
    )
    zones = (
        work.groupby("SHOT_ZONE_BASIC")
        .agg(
            attempts=("SHOT_MADE_FLAG", "size"),
            makes=("SHOT_MADE_FLAG", "sum"),
            points=("points", "sum"),
        )
        .reset_index()
    )
    zones["fg_pct"] = zones["makes"] / zones["attempts"]
    zones["pps"] = zones["points"] / zones["attempts"]
    return zones.sort_values("attempts", ascending=False).reset_index(drop=True)


def _court_shapes() -> list[dict]:
    """Minimal half-court geometry in stats.nba.com coordinates (hoop at 0,0)."""
    line = {"line_color": COURT_LINE, "line_width": 1.5}
    return [
        # Hoop and backboard.
        dict(type="circle", x0=-7.5, y0=-7.5, x1=7.5, y1=7.5, **line),
        dict(type="line", x0=-30, y0=-12.5, x1=30, y1=-12.5, **line),
        # Paint.
        dict(type="rect", x0=-80, y0=-47.5, x1=80, y1=142.5, **line),
        # Free-throw circle.
        dict(type="circle", x0=-60, y0=82.5, x1=60, y1=202.5, **line),
        # Corner-three lines.
        dict(type="line", x0=-220, y0=-47.5, x1=-220, y1=92.5, **line),
        dict(type="line", x0=220, y0=-47.5, x1=220, y1=92.5, **line),
        # Three-point arc (circle clipped by the plot range).
        dict(type="circle", x0=-237.5, y0=-237.5, x1=237.5, y1=237.5, **line),
        # Baseline and half-court line.
        dict(type="line", x0=-250, y0=-47.5, x1=250, y1=-47.5, **line),
        dict(type="line", x0=-250, y0=422.5, x1=250, y1=422.5, **line),
    ]


def render_shot_chart(shots: pd.DataFrame) -> None:
    """Scatter every shot on the half-court, made vs missed."""
    if shots.empty:
        st.info("No shots match the current filters.")
        return

    # Design data-color language: made = solid good/green, missed = open weak/red.
    fig = go.Figure()
    for made, name, color, symbol in (
        (1, "Made", COLOR_GOOD, "circle"),
        (0, "Missed", COLOR_WEAK, "circle-open"),
    ):
        subset = shots.loc[shots["SHOT_MADE_FLAG"] == made]
        fig.add_trace(
            go.Scattergl(
                x=subset["LOC_X"],
                y=subset["LOC_Y"],
                mode="markers",
                name=name,
                marker=dict(color=color, size=5, symbol=symbol, opacity=0.55),
                customdata=subset[["PLAYER_NAME", "SHOT_DISTANCE", "ACTION_TYPE"]],
                hovertemplate=(
                    "%{customdata[0]} — %{customdata[2]}<br>%{customdata[1]} ft<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        shapes=_court_shapes(),
        xaxis=dict(range=[-260, 260], visible=False, fixedrange=True),
        yaxis=dict(range=[-60, 440], visible=False, scaleanchor="x", scaleratio=1),
        height=620,
        legend=dict(orientation="h", yanchor="bottom", y=1.0),
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
