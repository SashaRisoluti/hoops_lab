"""Shared team rail + season switcher (design Option B, with CDN logos).

Rendered on every page right under the command bar: 30 clickable logo chips
grouped WEST | EAST, the selected franchise enlarged with its accent ring,
and the season selector beside it. Selection is global (session state) and
survives page changes; clicks travel through a ``?team=XXX`` query param.

Logos are hotlinked from the NBA CDN and fetched by the *browser*, so they
work on HF Spaces without committing trademarked assets to the repo; the
tricode title is the fallback.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.theme import (
    BG_CARD,
    BORDER,
    BORDER_SOFT,
    COLOR_PRIMARY,
    CONFERENCES,
    TEAM_ACCENTS_READABLE,
    TEXT_FAINT,
    hex_to_rgba,
)
from hoops_lab.config import REFERENCE_TEAM
from hoops_lab.storage.database import Database

_LOGO_URL = "https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"


def logo_url(team_id: int) -> str:
    """NBA CDN primary logo for a team id."""
    return _LOGO_URL.format(team_id=team_id)


def build_rail_html(abbr_to_id: dict[str, int], selected: str) -> str:
    """The 30-chip rail as clickable HTML (pure; selection drives the accent)."""
    accent = TEAM_ACCENTS_READABLE.get(selected, COLOR_PRIMARY)

    def chip(abbr: str) -> str:
        url = logo_url(abbr_to_id[abbr])
        if abbr == selected:
            style = (
                f"width:40px;height:40px;border:2px solid {accent};"
                f"box-shadow:0 0 0 3px {hex_to_rgba(accent, 0.22)};"
            )
            img = f'<img src="{url}" alt="{abbr}" style="width:26px;height:26px;">'
        else:
            style = f"width:32px;height:32px;border:1px solid {BORDER_SOFT};"
            img = f'<img src="{url}" alt="{abbr}" style="width:20px;height:20px;opacity:0.85;">'
        return (
            f'<a href="?team={abbr}" target="_self" title="{abbr}" '
            f'style="{style}border-radius:50%;background:{BG_CARD};display:inline-flex;'
            'align-items:center;justify-content:center;text-decoration:none;flex-shrink:0;">'
            f"{img}</a>"
        )

    def group(label: str, tricodes: list[str]) -> str:
        chips = "".join(chip(a) for a in tricodes)
        return (
            f'<span style="font-family:ui-monospace,monospace;font-size:9px;'
            f'letter-spacing:0.12em;color:{TEXT_FAINT};margin:0 4px;flex-shrink:0;">{label}</span>'
            f'<span style="display:inline-flex;gap:5px;align-items:center;">{chips}</span>'
        )

    divider = f'<span style="width:1px;height:28px;background:{BORDER};margin:0 8px;"></span>'
    return (
        '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:4px 0 2px;">'
        f"{group('WEST', CONFERENCES['WEST'])}{divider}{group('EAST', CONFERENCES['EAST'])}</div>"
    )


@st.cache_data
def _teams(_db: Database) -> pd.DataFrame:
    return _db.query_df("SELECT team_id, full_name, abbreviation FROM teams ORDER BY full_name")


@st.cache_data
def _seasons(_db: Database) -> list[str]:
    return _db.query_df("SELECT season FROM seasons ORDER BY season DESC")["season"].tolist()


def render_team_rail(database: Database) -> tuple[int, str, str]:
    """Render the rail + season selector; return (team_id, abbreviation, season)."""
    teams = _teams(database)
    abbr_to_id = dict(zip(teams["abbreviation"], teams["team_id"], strict=True))

    if "team" in st.query_params:
        choice = st.query_params["team"]
        if choice in abbr_to_id:
            st.session_state.rail_team = choice
        del st.query_params["team"]

    if "rail_team" not in st.session_state:
        reference = teams.loc[teams["full_name"] == REFERENCE_TEAM, "abbreviation"]
        st.session_state.rail_team = reference.iloc[0] if len(reference) else "DAL"
    selected = st.session_state.rail_team

    rail_col, season_col = st.columns([6.0, 0.85])
    rail_col.markdown(build_rail_html(abbr_to_id, selected), unsafe_allow_html=True)
    season = season_col.selectbox(
        "Season", _seasons(database), key="rail_season", label_visibility="collapsed"
    )
    return int(abbr_to_id[selected]), selected, season
