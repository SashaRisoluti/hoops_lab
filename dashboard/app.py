"""Hoops Lab — Streamlit dashboard entry point (home page)."""

import sys
from pathlib import Path

# Ensure the repo root is importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from hoops_lab import __version__  # noqa: E402
from hoops_lab.config import DEMO_SEASONS, ENVIRONMENT, REFERENCE_TEAM  # noqa: E402

st.set_page_config(page_title="Hoops Lab", page_icon="🏀", layout="wide")

st.title("🏀 Hoops Lab")
st.caption(
    f"v{__version__} — NBA data-science workbench: historical analysis, "
    "pre-game scouting, live game intelligence."
)

col1, col2, col3 = st.columns(3)
col1.metric("Reference team", REFERENCE_TEAM)
col2.metric("Demo seasons", ", ".join(DEMO_SEASONS))
col3.metric("Environment", ENVIRONMENT)

st.markdown(
    """
Use the **sidebar** to navigate the analysis sections:

| Section | Roadmap |
|---|---|
| 📊 Historical Stats Explorer | Phase 1 — in progress |
| 🧬 Player Analyzer | Phase 2 |
| 🛡️ Team Identity · 🔎 Opponent Scouting · ⚔️ Matchup Analysis · 🎯 Shot Map | Phase 3 |
| 🧩 Lineup Explorer | Phase 4 |
| 📡 Live Command Center | Phase 5 |
| 📝 Post-Game Review | Phase 6 |
"""
)

st.info("🚧 Project under active development — Phase 1 (Historical Dashboard) is being built.")
