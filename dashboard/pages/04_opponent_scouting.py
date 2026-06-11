"""Opponent Scouting — identity snapshot, strengths/weaknesses, players, lineups.

Tendencies are stats-based (Four Factors, usage hierarchy, lineup +/-);
play-type frequencies arrive with the possession data (Phase 4+).
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components.data_access import (  # noqa: E402
    get_database,
    team_options,
)
from dashboard.components.shot_archetypes_section import (  # noqa: E402
    render_shot_archetypes_section,
)
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import inject_theme, render_command_bar  # noqa: E402
from hoops_lab.analytics.opponent_scouting import (  # noqa: E402
    strengths_weaknesses,
    top_lineups,
    top_players,
)
from hoops_lab.analytics.team_identity import league_ratings, league_team_factors  # noqa: E402

st.set_page_config(page_title="Opponent Scouting", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Scouting")
st.title("🔎 Opponent Scouting")

database = get_database()
if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)

teams = team_options(database)
opponent_id = team_id  # the rail selects the team being scouted
opponent_name = teams.loc[teams["team_id"] == opponent_id, "full_name"].iloc[0]

# ---- Identity snapshot -------------------------------------------------------
ratings = league_ratings(database, season)
opp = ratings.loc[ratings["TEAM_ID"] == opponent_id].iloc[0]

st.subheader(f"{opponent_name} — {season}")
cols = st.columns(4)
cols[0].metric("Record", f"{int(opp['W'])}-{int(opp['L'])}")
cols[1].metric(
    "Off. rating",
    f"{opp['OFF_RATING']:.1f}",
    f"{opp['OFF_RATING_PCTL']:.0f}th pctl",
    delta_color="off",
)
cols[2].metric(
    "Def. rating",
    f"{opp['DEF_RATING']:.1f}",
    f"{opp['DEF_RATING_PCTL']:.0f}th pctl",
    delta_color="off",
)
cols[3].metric(
    "Net rating",
    f"{opp['NET_RATING']:+.1f}",
    f"{opp['NET_RATING_PCTL']:.0f}th pctl",
    delta_color="off",
)

# ---- Strengths / weaknesses --------------------------------------------------
league = league_team_factors(database, season)
strengths, weaknesses = strengths_weaknesses(league, opponent_id)

strengths_col, weaknesses_col = st.columns(2)
with strengths_col:
    st.subheader("✅ Strengths")
    for bullet in strengths:
        st.markdown(f"- {bullet}")
with weaknesses_col:
    st.subheader("⚠️ Weaknesses")
    for bullet in weaknesses:
        st.markdown(f"- {bullet}")

st.divider()

# ---- Key players & lineups -----------------------------------------------------
st.subheader("🎯 Offensive hierarchy (by usage)")
st.dataframe(
    top_players(database, opponent_id, season),
    hide_index=True,
    use_container_width=True,
)

st.subheader("🧩 Most effective lineups (min 50')")
lineups = top_lineups(database, opponent_id, season)
st.dataframe(
    lineups,
    hide_index=True,
    use_container_width=True,
    column_config={
        "pm_per48": st.column_config.NumberColumn("+/- per 48'", format="%+.1f"),
        "minutes": st.column_config.NumberColumn(format="%.0f"),
    },
)
st.caption(
    "Stats-based scouting from box scores and the complete lineup population; "
    "play-type tendencies (isolation, pick-and-roll, ...) arrive with the "
    "possession data in Phase 4+."
)

st.divider()

# ---- Shot archetypes (league-wide unsupervised shot-profile analysis) ---------
render_shot_archetypes_section(database, opponent_id, team_abbr, season)
