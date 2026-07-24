"""Design system — Worldcup26 restyle (spec docs/superpowers/specs/2026-07-24).

Deep navy surfaces with a fixed data-color language:
**green = good (>=66th pctl), yellow = mid (33rd-66th), red = weak (<33rd)** —
the same semantics on every chart so any reader decodes them instantly.
Electric blue is the primary/interactive color (selection, nav active).
Team accents re-theme the rail ring, header stripe and logo only; the
data-color language never changes.
"""

from __future__ import annotations

import copy
import json

import streamlit as st

# ---- Surfaces (Worldcup26 navy family) --------------------------------------
BG_PAGE = "#070b14"
BG_FRAME = "#0b0f19"
BG_BAR = "#0b0f19"
BG_CARD = "#0f172a"
BG_TILE = "#141c2e"
BORDER_DARK = "#0e1320"
BORDER = "#111829"
BORDER_SOFT = "#1a2338"
GRID = "#1c2740"
COURT_LINE = "#33415e"
TEXT = "#f1f5f9"
TEXT_SOFT = "#9ca3af"
TEXT_MUTED = "#64748b"
TEXT_FAINT = "#475569"

# ---- Data semantics ---------------------------------------------------------
COLOR_GOOD = "#16c47f"  # >=66th percentile
COLOR_MID = "#ffd100"  # 33rd-66th percentile
COLOR_WEAK = "#e0262c"  # <33rd percentile
COLOR_PRIMARY = "#0052ff"  # selection, nav active, interactive elements
COLOR_SPECIAL = "#a855f7"  # model/AI-derived flags
COLOR_PRIMARY_SOFT = "#4d7fff"  # readable primary for small text / thin lines
COLOR_WEAK_SOFT = "#ff5a63"  # readable weak for small text

# ---- Legacy aliases (Phase A only — deleted in Phase B) ---------------------
ORANGE = COLOR_GOOD
BLUE = COLOR_MID
BLUE_TEXT = COLOR_PRIMARY_SOFT
RED = COLOR_WEAK
RED_TEXT = COLOR_WEAK_SOFT

FONT_BODY = "Inter, sans-serif"
FONT_DISPLAY = "'Inter Tight', sans-serif"
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
    """Bar/marker color for a league percentile (fixed data-color rule)."""
    if percentile >= 66:
        return COLOR_GOOD
    if percentile >= 33:
        return COLOR_MID
    return COLOR_WEAK


def pctl_text_color(percentile: float) -> str:
    """Readable text variant of :func:`pctl_color`."""
    if percentile >= 66:
        return COLOR_GOOD
    if percentile >= 33:
        return COLOR_MID
    return COLOR_WEAK_SOFT


#: Design tokens as one portable mapping (React/Tailwind port seed).
TOKENS: dict[str, str] = {
    "bg_page": BG_PAGE,
    "bg_frame": BG_FRAME,
    "bg_card": BG_CARD,
    "bg_tile": BG_TILE,
    "border": BORDER,
    "border_dark": BORDER_DARK,
    "border_soft": BORDER_SOFT,
    "grid": GRID,
    "court_line": COURT_LINE,
    "text": TEXT,
    "text_soft": TEXT_SOFT,
    "text_muted": TEXT_MUTED,
    "text_faint": TEXT_FAINT,
    "good": COLOR_GOOD,
    "mid": COLOR_MID,
    "weak": COLOR_WEAK,
    "primary": COLOR_PRIMARY,
    "special": COLOR_SPECIAL,
    "primary_soft": COLOR_PRIMARY_SOFT,
    "weak_soft": COLOR_WEAK_SOFT,
    "font_body": FONT_BODY,
    "font_display": FONT_DISPLAY,
    "font_mono": FONT_MONO,
}


def tokens_json() -> str:
    """Serialize the design tokens to JSON (React/Tailwind port seed)."""
    return json.dumps(TOKENS, indent=2)


_PLOTLY_LAYOUT: dict = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=FONT_BODY, color=TEXT),
    margin=dict(l=10, r=10, t=10, b=10),
)


def plotly_layout() -> dict:
    """Fresh copy of the shared Plotly layout kwargs.

    Returns:
        A deep copy — callers may mutate it without affecting other figures.
    """
    return copy.deepcopy(_PLOTLY_LAYOUT)


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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Inter+Tight:wght@600;700;800;900&display=swap" rel="stylesheet">
<style>
  html, body, [data-testid="stAppViewContainer"] {{
    background: {BG_PAGE}; font-family: {FONT_BODY}; color: {TEXT};
  }}
  [data-testid="stHeader"] {{ background: {BG_PAGE}; }}
  h1, h2, h3 {{ font-family: {FONT_DISPLAY}; font-weight: 800; letter-spacing: -0.01em; }}
  [data-testid="stSidebar"] {{ background: {BG_BAR}; border-right: 1px solid {BORDER_DARK}; }}
  /* Command bar page links */
  div[data-testid="stPageLink"] a {{
    font-size: 13px; font-weight: 500; color: {TEXT_MUTED} !important;
    padding: 4px 12px; border-radius: 7px; text-decoration: none;
  }}
  div[data-testid="stPageLink"] a:hover {{ color: {TEXT} !important; background: {BG_TILE}; }}
  div[data-testid="stPageLink"] a[aria-current="page"] {{
    color: {TEXT} !important; background: {BG_TILE}; box-shadow: inset 0 -2px 0 {COLOR_PRIMARY};
  }}
  /* Team-rail buttons: circular tricode chips */
  div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    width: 34px; height: 34px; min-height: 34px; padding: 0; border-radius: 50%;
    background: {BG_CARD}; border: 1px solid {BORDER_SOFT};
    font-family: {FONT_MONO}; font-size: 9px; color: {TEXT_MUTED};
  }}
  div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    border-color: {COLOR_PRIMARY_SOFT}; color: {TEXT};
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
  <div style="width:22px;height:22px;border-radius:50%;background:{COLOR_PRIMARY};position:relative;overflow:hidden;">
    <div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:2px;background:{BG_BAR};transform:translateX(-50%);"></div>
    <div style="position:absolute;top:50%;left:-2px;right:-2px;height:2px;background:{BG_BAR};transform:translateY(-50%);"></div>
  </div>
  <div style="font-family:{FONT_DISPLAY};font-size:19px;font-weight:800;letter-spacing:0.08em;color:{TEXT};">HOOPS&nbsp;LAB</div>
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
