"""Interactive distribution histogram with player marker and percentile label."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from hoops_lab.features.percentiles import percentile_rank


def render_percentile_histogram(df: pd.DataFrame, stat_options: list[str]) -> None:
    """Histogram of one stat across the filtered population + selected player.

    Percentiles are computed against ``df`` as passed in — i.e. the filtered
    population, never the full universe (project rule).
    """
    st.subheader("📈 Percentile analyzer")
    if df.empty or not stat_options:
        st.info("Select at least one statistic and widen the filters to populate the histogram.")
        return

    labels = df["PLAYER_NAME"].astype(str) + " (" + df["season"].astype(str) + ")"
    col1, col2 = st.columns(2)
    row_idx = col1.selectbox(
        "Player", options=list(range(len(df))), format_func=lambda i: labels.iloc[i]
    )
    stat = col2.selectbox("Statistic", stat_options)

    series = df[stat]
    value = series.iloc[row_idx]
    if pd.isna(value):
        st.warning(f"{labels.iloc[row_idx]} has no value for {stat}.")
        return
    percentile = percentile_rank(series).iloc[row_idx]

    fig = px.histogram(df, x=stat, nbins=30)
    fig.add_vline(
        x=float(value),
        line_width=3,
        line_color="crimson",
        annotation_text=f"{percentile:.0f}th pctl",
        annotation_position="top",
    )
    fig.update_layout(
        showlegend=False, bargap=0.05, height=420, xaxis_title=stat, yaxis_title="Players"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"**{labels.iloc[row_idx]}** is in the **{percentile:.0f}th percentile** for **{stat}** "
        f"({value:.2f}) within the filtered population (n = {len(df)} player-seasons)."
    )
