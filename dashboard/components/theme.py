"""Design system from the Claude Design handoff (Hoops Lab Dashboard v2).

Dark broadcast look in NBA tricolor with a fixed data-color language:
**orange = good (>=66th pctl), blue = mid (33rd-66th), red = weak (<33rd)** —
the same semantics on every chart so any reader decodes them instantly.
Team accents re-theme the rail ring, header stripe and logo only; the
tricolor data language never changes.
"""

from __future__ import annotations

import streamlit as st

# ---- Tokens (verbatim from the design file) ---------------------------------
BG_PAGE = "#101214"
BG_FRAME = "#0C0E12"
BG_BAR = "#0E1117"
BG_CARD = "#14171D"
BG_TILE = "#0E1117"
BORDER_DARK = "#20252F"
BORDER = "#242A36"
BORDER_SOFT = "#2A3140"
GRID = "#222834"
COURT_LINE = "#3A4254"
TEXT = "#EDEFF3"
TEXT_SOFT = "#C7CDD9"
TEXT_MUTED = "#8B93A3"
TEXT_FAINT = "#6B7384"

ORANGE = "#F0703A"
BLUE = "#2E5FB7"
BLUE_TEXT = "#5B8AE0"
RED = "#D2243C"
RED_TEXT = "#E25A6E"

FONT_BODY = "Barlow, sans-serif"
FONT_DISPLAY = "'Barlow Condensed', sans-serif"
FONT_MONO = "ui-monospace, monospace"

#: Franchise accent per tricode (readable on the dark background).
TEAM_ACCENTS: dict[str, str] = {
    "ATL": "#E03A3E",
    "BOS": "#007A33",
    "BKN": "#9BA3AE",
    "CHA": "#00788C",
    "CHI": "#CE1141",
    "CLE": "#FDBB30",
    "DAL": "#0064B1",
    "DEN": "#FEC524",
    "DET": "#C8102E",
    "GSW": "#FFC72C",
    "HOU": "#CE1141",
    "IND": "#FDBB30",
    "LAC": "#C8102E",
    "LAL": "#FDB927",
    "MEM": "#5D76A9",
    "MIA": "#F9A01B",
    "MIL": "#1B8A5A",
    "MIN": "#78BE20",
    "NOP": "#85714D",
    "NYK": "#F58426",
    "OKC": "#007AC1",
    "ORL": "#0077C0",
    "PHI": "#006BB6",
    "PHX": "#E56020",
    "POR": "#E03A3E",
    "SAC": "#5A2D81",
    "SAS": "#C4CED4",
    "TOR": "#CE1141",
    "UTA": "#F9A01B",
    "WAS": "#E31837",
}

#: Conference grouping for the team rail (design order, West | East).
CONFERENCES: dict[str, list[str]] = {
    "WEST": [
        "DAL",
        "DEN",
        "GSW",
        "HOU",
        "LAC",
        "LAL",
        "MEM",
        "MIN",
        "NOP",
        "OKC",
        "PHX",
        "POR",
        "SAC",
        "SAS",
        "UTA",
    ],
    "EAST": [
        "ATL",
        "BOS",
        "BKN",
        "CHA",
        "CHI",
        "CLE",
        "DET",
        "IND",
        "MIA",
        "MIL",
        "NYK",
        "ORL",
        "PHI",
        "TOR",
        "WAS",
    ],
}


def pctl_color(percentile: float) -> str:
    """Bar/marker color for a league percentile (design tricolor rule)."""
    if percentile >= 66:
        return ORANGE
    if percentile >= 33:
        return BLUE
    return RED


def pctl_text_color(percentile: float) -> str:
    """Readable text variant of :func:`pctl_color`."""
    if percentile >= 66:
        return ORANGE
    if percentile >= 33:
        return BLUE_TEXT
    return RED_TEXT


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """'#RRGGBB' -> 'rgba(r,g,b,a)' (for accent gradients and glows)."""
    value = hex_color.lstrip("#")
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def inject_theme() -> None:
    """Global CSS: fonts, dark surfaces, command-bar/page-link styling."""
    st.markdown(
        f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  html, body, [data-testid="stAppViewContainer"] {{
    background: {BG_PAGE}; font-family: {FONT_BODY}; color: {TEXT};
  }}
  [data-testid="stHeader"] {{ background: {BG_PAGE}; }}
  h1, h2, h3 {{ font-family: {FONT_DISPLAY}; letter-spacing: 0.04em; text-transform: uppercase; }}
  [data-testid="stSidebar"] {{ background: {BG_BAR}; border-right: 1px solid {BORDER_DARK}; }}
  /* Command bar page links */
  div[data-testid="stPageLink"] a {{
    font-size: 13px; font-weight: 500; color: {TEXT_MUTED} !important;
    padding: 4px 12px; border-radius: 7px; text-decoration: none;
  }}
  div[data-testid="stPageLink"] a:hover {{ color: {TEXT} !important; background: #161B23; }}
  div[data-testid="stPageLink"] a[aria-current="page"] {{
    color: {TEXT} !important; background: #1A1F29; box-shadow: inset 0 -2px 0 {ORANGE};
  }}
  /* Team-rail buttons: circular tricode chips */
  div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    width: 34px; height: 34px; min-height: 34px; padding: 0; border-radius: 50%;
    background: {BG_CARD}; border: 1px solid {BORDER_SOFT};
    font-family: {FONT_MONO}; font-size: 9px; color: {TEXT_MUTED};
  }}
  div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    border-color: {BLUE_TEXT}; color: {TEXT};
  }}
</style>
""",
        unsafe_allow_html=True,
    )


def render_command_bar(active: str) -> None:
    """Top command-bar navigation (replaces the sidebar page list).

    Parameters
    ----------
    active:
        Label of the current page (visual context; the active state itself
        is resolved by Streamlit via aria-current).
    """
    with st.container():
        cols = st.columns([2.2, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.4])
        cols[0].markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;padding-top:2px;">
  <div style="width:22px;height:22px;border-radius:50%;background:{ORANGE};position:relative;overflow:hidden;">
    <div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:2px;background:{BG_BAR};transform:translateX(-50%);"></div>
    <div style="position:absolute;top:50%;left:-2px;right:-2px;height:2px;background:{BG_BAR};transform:translateY(-50%);"></div>
  </div>
  <div style="font-family:{FONT_DISPLAY};font-size:19px;font-weight:700;letter-spacing:0.08em;color:{TEXT};">HOOPS&nbsp;LAB</div>
</div>""",
            unsafe_allow_html=True,
        )
        links = [
            ("app.py", "Overview"),
            ("pages/01_historical_explorer.py", "Explorer"),
            ("pages/02_player_analyzer.py", "Players"),
            ("pages/04_opponent_scouting.py", "Scouting"),
            ("pages/05_matchup_analysis.py", "Matchup"),
            ("pages/06_shot_map.py", "Shots"),
            ("pages/07_lineup_explorer.py", "Lineups"),
            ("pages/08_live_command_center.py", "🔴 Live"),
            ("pages/09_post_game_review.py", "Reports"),
        ]
        for col, (page, label) in zip(cols[1:], links, strict=True):
            try:
                col.page_link(page, label=label)
            except Exception:
                # Outside the multipage runtime (AppTest on a single file)
                # page links cannot resolve — degrade to a static label.
                col.markdown(
                    f'<span style="font-size:13px;color:{TEXT_MUTED};">{label}</span>',
                    unsafe_allow_html=True,
                )
    st.markdown(
        f'<div style="height:1px;background:{BORDER_DARK};margin:2px 0 14px;"></div>',
        unsafe_allow_html=True,
    )
