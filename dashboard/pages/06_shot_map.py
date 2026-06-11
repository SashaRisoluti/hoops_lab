"""Shot Map — every shot on the half-court, zone efficiency, assisted share.

The team dropdown lists every team with shot-location data (the reference
team by default, per the demo data strategy — it grows automatically when
more teams' shot charts are downloaded). The assisted share is recovered by
joining play-by-play descriptions, so it covers the sampled games.
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
from dashboard.components.theme import inject_theme, render_command_bar  # noqa: E402
from hoops_lab.analytics.shot_context import assisted_summary  # noqa: E402

st.set_page_config(page_title="Shot Map", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Shots")
st.title("🎯 Shot Map")

database = get_database()
if database.table_rows("shots") == 0:
    st.warning("No shot data loaded — run the downloader and the seeder first (see README).")
    st.stop()

teams_with_shots = database.query_df(
    """
    SELECT DISTINCT s.TEAM_ID, t.full_name
    FROM shots AS s
    JOIN teams AS t ON t.team_id = s.TEAM_ID
    ORDER BY t.full_name
    """
)

st.sidebar.header("🔍 Filters")
team_name = st.sidebar.selectbox("Team", teams_with_shots["full_name"].tolist())
team_id = int(teams_with_shots.loc[teams_with_shots["full_name"] == team_name, "TEAM_ID"].iloc[0])

season_options = database.query_df(
    "SELECT DISTINCT season FROM shots WHERE TEAM_ID = ? ORDER BY season DESC", [team_id]
)["season"].tolist()
season = st.sidebar.selectbox("Season", season_options)

player_options = database.query_df(
    "SELECT DISTINCT PLAYER_NAME FROM shots WHERE season = ? AND TEAM_ID = ? ORDER BY PLAYER_NAME",
    [season, team_id],
)["PLAYER_NAME"].tolist()
players = st.sidebar.multiselect("Players (empty = whole team)", player_options)
outcome = st.sidebar.radio("Outcome", ["All", "Made only", "Missed only"], horizontal=True)

st.caption(
    f"Shot-location data available for **{len(teams_with_shots)} team(s)** — add more with "
    "`HistoricalDownloader.download_shot_chart` and re-seed."
)

sql = "SELECT * FROM shots WHERE season = ? AND TEAM_ID = ?"
params: list = [season, team_id]
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

    st.subheader("🤝 Assisted makes")
    assisted = assisted_summary(database, shots) if not shots.empty else None
    if assisted is None:
        st.info("No play-by-play coverage for the filtered shots.")
    else:
        ast_cols = st.columns(3)
        ast_cols[0].metric("Assisted share", f"{assisted['share']:.0%}")
        ast_cols[1].metric("Makes covered", assisted["made_covered"])
        ast_cols[2].metric("Games covered", assisted["games_covered"])
        st.caption(
            "From play-by-play descriptions — limited to the sampled games; "
            "extend the PBP download to widen coverage."
        )
