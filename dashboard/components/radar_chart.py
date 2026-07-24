"""Percentile-based radar chart (plotly Scatterpolar)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from dashboard.components.theme import COLOR_PRIMARY, COLOR_PRIMARY_SOFT, hex_to_rgba, plotly_layout


def render_radar_chart(values: dict[str, float], title: str = "") -> None:
    """Render a closed radar of 0-100 percentile values."""
    if not values:
        st.info("Not enough data for the percentile radar.")
        return

    categories = list(values)
    radii = [values[c] for c in categories]
    line_color = COLOR_PRIMARY_SOFT
    fillcolor = hex_to_rgba(COLOR_PRIMARY, 0.25)
    fig = go.Figure(
        go.Scatterpolar(
            r=radii + radii[:1],
            theta=categories + categories[:1],
            fill="toself",
            line_color=line_color,
            fillcolor=fillcolor,
            hovertemplate="%{theta}: %{r:.0f}th pctl<extra></extra>",
        )
    )
    fig.update_layout(
        **plotly_layout(),
        title=title,
        polar=dict(
            radialaxis=dict(
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                showticklabels=True,
                ticks="",
            )
        ),
        showlegend=False,
        height=430,
    )
    st.plotly_chart(fig, use_container_width=True)
