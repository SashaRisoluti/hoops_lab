"""Live KPI strip: score, game clock and per-team live efficiency."""

from __future__ import annotations

import re

import streamlit as st

from dashboard.components.stat_tile import stat_tile_html
from hoops_lab.live.game_state import GameState

_CLOCK = re.compile(r"PT(\d+)M([\d.]+)S")


def _pretty_clock(period: int, clock: str) -> str:
    match = _CLOCK.search(clock or "")
    if not match:
        return f"Q{period}"
    label = f"Q{period}" if period <= 4 else f"OT{period - 4}"
    return f"{label} · {int(match.group(1))}:{int(float(match.group(2))):02d}"


def render_kpi_strip(state: GameState, home_label: str, away_label: str) -> None:
    """Score header + the live efficiency metrics for both teams."""
    score_home, score_away = state.score
    st.subheader(f"{home_label} {score_home} — {score_away} {away_label}")
    st.caption(
        f"{_pretty_clock(state.period, state.clock)} · "
        f"{state.events_seen} events · {len(state.possessions)} possessions"
    )

    home, away = state.team_stats[state.home_id], state.team_stats[state.away_id]
    home_ppp, away_ppp = state.ppp(state.home_id), state.ppp(state.away_id)
    pace = state.pace_estimate

    cols = st.columns(7)
    cols[0].markdown(
        stat_tile_html(
            f"{home_label} eFG%", f"{home.efg_pct:.1%}" if home.efg_pct is not None else "—"
        ),
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        stat_tile_html(f"{home_label} PPP", f"{home_ppp:.2f}" if home_ppp is not None else "—"),
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        stat_tile_html(f"{home_label} TOV", home.tov),
        unsafe_allow_html=True,
    )
    cols[3].markdown(
        stat_tile_html("Pace", f"{pace:.1f}" if pace is not None else "—"),
        unsafe_allow_html=True,
    )
    cols[4].markdown(
        stat_tile_html(
            f"{away_label} eFG%", f"{away.efg_pct:.1%}" if away.efg_pct is not None else "—"
        ),
        unsafe_allow_html=True,
    )
    cols[5].markdown(
        stat_tile_html(f"{away_label} PPP", f"{away_ppp:.2f}" if away_ppp is not None else "—"),
        unsafe_allow_html=True,
    )
    cols[6].markdown(
        stat_tile_html(f"{away_label} TOV", away.tov),
        unsafe_allow_html=True,
    )
