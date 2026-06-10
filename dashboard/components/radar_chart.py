"""Percentile-based radar chart (plotly Scatterpolar)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


def render_radar_chart(values: dict[str, float], title: str = "") -> None:
    """Render a closed radar of 0-100 percentile values."""
    if not values:
        st.info("Not enough data for the percentile radar.")
        return

    categories = list(values)
    radii = [values[c] for c in categories]
    fig = go.Figure(
        go.Scatterpolar(
            r=radii + radii[:1],
            theta=categories + categories[:1],
            fill="toself",
            line_color="#F97316",
            fillcolor="rgba(249, 115, 22, 0.25)",
            hovertemplate="%{theta}: %{r:.0f}th pctl<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100])),
        showlegend=False,
        height=430,
        margin=dict(l=60, r=60, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
