"""Hoops Lab — Streamlit dashboard entry point (home page)."""

import sys
from pathlib import Path

# Ensure the repo root is importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components.data_access import get_database  # noqa: E402
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

| Section | What you find |
|---|---|
| 📊 Historical Stats Explorer | Dynamic filters, custom stats table, percentile histogram |
| 🧬 Player Analyzer | Player card, percentile radar, lineup-based on/off |
| 🛡️ Team Identity · 🔎 Scouting · ⚔️ Matchup | Four Factors, auto scouting, leverage index |
| 🎯 Shot Map | Half-court shot chart, zone efficiency, assisted share |
| 🧩 Lineup Explorer | Complete 5-man lineups and exact player combinations |
| 📡 Live Command Center | Replay/live game state, tactical alerts, win probability |
| 📝 Post-Game Review | Automated report: factors, runs, shot quality, insights |
"""
)


database = get_database()

if database.table_rows("seasons") > 0:
    st.subheader("Loaded data")
    st.dataframe(
        database.query_df(
            "SELECT season, season_type, games, first_game, last_game FROM seasons ORDER BY season"
        ),
        hide_index=True,
    )
else:
    st.warning(
        "No data loaded yet — run `python -m hoops_lab.ingestion.historical` and "
        "`python -m hoops_lab.storage.seed` from the repo root."
    )
