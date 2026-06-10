"""Lineup Explorer — complete 5-man lineups and exact player combinations.

Built on the complete per-team lineup population (no server cap): offensive
metrics are exact-from-counts; defensive ratings are not derivable from the
Base measure, so plus/minus per 48 is the two-way signal.
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.components.data_access import (  # noqa: E402
    get_database,
    reference_team_index,
    team_options,
)
from hoops_lab.analytics.lineup_explorer import (  # noqa: E402
    enrich_lineups,
    filter_lineups_by_players,
    player_combinations,
)

LINEUP_COLUMNS = {
    "GROUP_NAME": st.column_config.TextColumn("lineup", width="large"),
    "MIN": st.column_config.NumberColumn("min", format="%.0f"),
    "PM_PER48": st.column_config.NumberColumn("+/- per 48", format="%+.1f"),
    "ORTG_EST": st.column_config.NumberColumn("ORtg est", format="%.1f"),
    "EFG_PCT_CALC": st.column_config.NumberColumn("eFG%", format="%.3f"),
    "TS_PCT_CALC": st.column_config.NumberColumn("TS%", format="%.3f"),
    "TOV_PCT_CALC": st.column_config.NumberColumn("TOV%", format="%.1f"),
    "POSS_EST": st.column_config.NumberColumn("poss est", format="%.0f"),
    "PLUS_MINUS": st.column_config.NumberColumn("+/-", format="%+.0f"),
}

st.set_page_config(page_title="Lineup Explorer", page_icon="🏀", layout="wide")
st.title("🧩 Lineup Explorer")

database = get_database()
if database.table_rows("lineups") == 0:
    st.warning("No lineup data loaded — run the downloader and the seeder first (see README).")
    st.stop()

season_options = database.query_df("SELECT season FROM seasons ORDER BY season DESC")[
    "season"
].tolist()
teams = team_options(database)

st.sidebar.header("🔍 Selection")
season = st.sidebar.selectbox("Season", season_options)
team_name = st.sidebar.selectbox(
    "Team", teams["full_name"].tolist(), index=reference_team_index(teams)
)
team_id = int(teams.loc[teams["full_name"] == team_name, "team_id"].iloc[0])

roster = database.query_df(
    "SELECT PLAYER_ID, PLAYER_NAME FROM player_season_full "
    "WHERE TEAM_ID = ? AND season = ? ORDER BY MIN DESC",
    [team_id, season],
)
name_to_id = dict(zip(roster["PLAYER_NAME"], roster["PLAYER_ID"], strict=True))
id_to_name = {int(v): k for k, v in name_to_id.items()}

with_names = st.sidebar.multiselect("With players", roster["PLAYER_NAME"].tolist())
without_names = st.sidebar.multiselect("Without players", roster["PLAYER_NAME"].tolist())
min_lineup_minutes = st.sidebar.slider("Min lineup minutes", 0, 300, 25, 5)

team_lineups = database.query_df(
    "SELECT * FROM lineups WHERE TEAM_ID = ? AND season = ?", [team_id, season]
)
filtered = filter_lineups_by_players(
    team_lineups,
    with_ids=[int(name_to_id[n]) for n in with_names],
    without_ids=[int(name_to_id[n]) for n in without_names],
)

five_man_tab, combos_tab = st.tabs(["5-man lineups", "Player combinations"])

with five_man_tab:
    lineups = enrich_lineups(filtered.loc[filtered["MIN"] >= min_lineup_minutes])
    lineups = lineups.sort_values("PM_PER48", ascending=False)
    st.caption(
        f"{len(lineups)} lineups ≥ {min_lineup_minutes}' "
        f"(of {len(filtered)} matching the player filters — complete population)."
    )
    st.dataframe(
        lineups[list(LINEUP_COLUMNS)],
        hide_index=True,
        use_container_width=True,
        column_config=LINEUP_COLUMNS,
    )

    if not lineups.empty:
        st.subheader("Net impact vs volume")
        fig = px.scatter(
            lineups,
            x="POSS_EST",
            y="PM_PER48",
            size="MIN",
            hover_name="GROUP_NAME",
            color="ORTG_EST",
            color_continuous_scale="RdYlGn",
        )
        fig.add_hline(y=0, line_dash="dot", line_color="#888")
        fig.update_layout(
            height=420, xaxis_title="Estimated possessions", yaxis_title="+/- per 48'"
        )
        st.plotly_chart(fig, use_container_width=True)

with combos_tab:
    size = st.radio("Combination size", [2, 3], horizontal=True)
    min_combo_minutes = st.slider("Min combination minutes", 0, 1500, 200, 25)

    combos = player_combinations(filtered, size=size, min_minutes=min_combo_minutes)
    if combos.empty:
        st.info("No combinations reach the minutes threshold with the current filters.")
    else:
        combos = combos.copy()
        combos["players_names"] = combos["players"].map(
            lambda ids: " · ".join(id_to_name.get(int(i), str(i)) for i in ids)
        )
        st.caption(
            f"{len(combos)} {size}-man combinations ≥ {min_combo_minutes}' — exact sums "
            "over every 5-man lineup containing the combo."
        )
        display_cols = {
            "players_names": st.column_config.TextColumn("players", width="large"),
            **{k: v for k, v in LINEUP_COLUMNS.items() if k != "GROUP_NAME"},
        }
        st.dataframe(
            combos[list(display_cols)],
            hide_index=True,
            use_container_width=True,
            column_config=display_cols,
        )
