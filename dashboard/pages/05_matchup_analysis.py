"""Matchup Analysis — side-by-side Four Factors and the leverage index.

The leverage index is the Four-Factors adaptation of the spec formula
(attacker strength x defender weakness); the play-type-weighted version
arrives with the possession data (Phase 4+).
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
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import inject_theme, render_command_bar  # noqa: E402
from hoops_lab.analytics.matchup import matchup_leverage, matchup_table  # noqa: E402
from hoops_lab.analytics.team_identity import league_team_factors  # noqa: E402

st.set_page_config(page_title="Matchup Analysis", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Matchup")
st.title("⚔️ Matchup Analysis")

database = get_database()
if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)

teams = team_options(database)
team_a = team_id  # rail = my team
team_a_name = teams.loc[teams["team_id"] == team_a, "full_name"].iloc[0]

st.sidebar.header("🔍 Selection")
opponent_options = [n for n in teams["full_name"].tolist() if n != team_a_name]
team_b_name = st.sidebar.selectbox("Opponent", opponent_options)
team_b = int(teams.loc[teams["full_name"] == team_b_name, "team_id"].iloc[0])

if team_a == team_b:
    st.info("Pick two different teams to compare.")
    st.stop()

league = league_team_factors(database, season)

# ---- Side-by-side Four Factors ----------------------------------------------
st.subheader(f"{team_a_name} vs {team_b_name} — {season}")
comparison = matchup_table(league, team_a, team_b)
st.dataframe(comparison, hide_index=True, use_container_width=True)

st.divider()

# ---- Leverage index -----------------------------------------------------------
st.subheader("🎯 Matchup leverage — where to attack")
leverage = matchup_leverage(league, team_a, team_b)
st.dataframe(
    leverage[["attacking_team", "label", "attacker_pctl", "defender_pctl", "leverage"]],
    hide_index=True,
    use_container_width=True,
    column_config={
        "attacker_pctl": st.column_config.NumberColumn("attacker pctl", format="%.0f"),
        "defender_pctl": st.column_config.NumberColumn("defender pctl", format="%.0f"),
        "leverage": st.column_config.ProgressColumn(
            "leverage", min_value=0, max_value=100, format="%.0f"
        ),
    },
)

best = leverage.iloc[0]
st.caption(
    f"Top opportunity: **{best['attacking_team']}** attacking through "
    f"**{best['label']}** (leverage {best['leverage']:.0f}/100). "
    "Leverage = (attacker offensive percentile + defender defensive weakness) / 2; "
    "the play-type-weighted version of the spec formula arrives with possession data."
)
