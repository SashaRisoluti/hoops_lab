"""Shot Map — every shot on the half-court + zone efficiency.

Shot-location data is downloaded for the reference team only (public-demo
data strategy); extend the ingestion to more teams when needed.
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.shot_chart import render_shot_chart, zone_efficiency  # noqa: E402
from hoops_lab.config import REFERENCE_TEAM  # noqa: E402

st.set_page_config(page_title="Shot Map", page_icon="🏀", layout="wide")
st.title("🎯 Shot Map")

database = get_database()
if database.table_rows("shots") == 0:
    st.warning("No shot data loaded — run the downloader and the seeder first (see README).")
    st.stop()

st.caption(
    f"Shot-location data covers **{REFERENCE_TEAM}** (demo data strategy); "
    "swap the team via REFERENCE_TEAM and re-run the downloader."
)

season_options = database.query_df("SELECT DISTINCT season FROM shots ORDER BY season DESC")[
    "season"
].tolist()

st.sidebar.header("🔍 Filters")
season = st.sidebar.selectbox("Season", season_options)
player_options = database.query_df(
    "SELECT DISTINCT PLAYER_NAME FROM shots WHERE season = ? ORDER BY PLAYER_NAME", [season]
)["PLAYER_NAME"].tolist()
players = st.sidebar.multiselect("Players (empty = whole team)", player_options)
outcome = st.sidebar.radio("Outcome", ["All", "Made only", "Missed only"], horizontal=True)

sql = "SELECT * FROM shots WHERE season = ?"
params: list = [season]
if players:
    sql += f" AND PLAYER_NAME IN ({', '.join('?' for _ in players)})"
    params.extend(players)
if outcome != "All":
    sql += " AND SHOT_MADE_FLAG = ?"
    params.append(1 if outcome == "Made only" else 0)

shots = database.query_df(sql, params)

chart_col, zones_col = st.columns([3, 2])
with chart_col:
    render_shot_chart(shots)
with zones_col:
    st.subheader("Zone efficiency")
    zones = zone_efficiency(shots) if not shots.empty else None
    if zones is None:
        st.info("No shots match the current filters.")
    else:
        st.dataframe(
            zones,
            hide_index=True,
            use_container_width=True,
            column_config={
                "fg_pct": st.column_config.NumberColumn("FG%", format="%.1%"),
                "pps": st.column_config.NumberColumn("PPS", format="%.2f"),
            },
        )
        made = int(shots["SHOT_MADE_FLAG"].sum())
        st.caption(
            f"{len(shots):,} shots · {made:,} made ({made / len(shots):.1%}) · "
            "PPS weighs threes at 3 points."
        )
