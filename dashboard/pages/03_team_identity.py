"""Team Identity — ratings, Four Factors vs the league, recent form."""

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
    team_options,
)
from dashboard.components.page_header import render_page_header  # noqa: E402
from dashboard.components.radar_chart import render_radar_chart  # noqa: E402
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import (  # noqa: E402
    GRID,
    inject_theme,
    plotly_layout,
    render_command_bar,
)
from hoops_lab.analytics.team_identity import (  # noqa: E402
    league_playmaking_rebounding,
    league_ratings,
    league_team_factors,
    team_game_factors,
)
from hoops_lab.features.four_factors import FACTOR_LABELS  # noqa: E402

RADAR_SHORT_LABELS = {
    "OFF_EFG": "eFG%",
    "OFF_TOV_PCT": "Ball security",
    "OFF_ORB_PCT": "Off. glass",
    "OFF_FT_RATE": "FT rate",
    "DEF_EFG": "Shot defense",
    "DEF_TOV_PCT": "Forced TOV",
    "DEF_ORB_PCT": "Def. glass",
    "DEF_FT_RATE": "Foul discipline",
}

st.set_page_config(page_title="Team Identity", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Team")
render_page_header("Team Identity", subtitle="Ratings, Four Factors and playmaking trends")

database = get_database()
if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)

teams = team_options(database)
team_name = teams.loc[teams["team_id"] == team_id, "full_name"].iloc[0]

# ---- Ratings ----------------------------------------------------------------
ratings = league_ratings(database, season)
team_ratings = ratings.loc[ratings["TEAM_ID"] == team_id].iloc[0]

st.subheader(f"{team_name} — {season}")
cols = st.columns(5)
cols[0].metric("Record", f"{int(team_ratings['W'])}-{int(team_ratings['L'])}")
for col, (label, column) in zip(
    cols[1:],
    (
        ("Offensive rating", "OFF_RATING"),
        ("Defensive rating", "DEF_RATING"),
        ("Net rating", "NET_RATING"),
        ("Pace", "PACE"),
    ),
    strict=True,
):
    delta = f"{team_ratings[f'{column}_PCTL']:.0f}th pctl" if f"{column}_PCTL" in ratings else None
    col.metric(label, f"{team_ratings[column]:.1f}", delta=delta, delta_color="off")

st.divider()

# ---- Four Factors -----------------------------------------------------------
league = league_team_factors(database, season)
team_row = league.loc[league["TEAM_ID"] == team_id].iloc[0]

radar_col, table_col = st.columns([3, 2])
with radar_col:
    st.subheader("📡 Four Factors radar (league percentiles)")
    render_radar_chart(
        {short: float(team_row[f"{factor}_PCTL"]) for factor, short in RADAR_SHORT_LABELS.items()}
    )

with table_col:
    st.subheader("Four Factors")
    rows = []
    for factor, label in FACTOR_LABELS.items():
        value = team_row[factor]
        formatted = f"{value:.1%}" if "EFG" in factor or "RATE" in factor else f"{value:.1f}%"
        rows.append({"factor": label, "value": formatted, "pctl": team_row[f"{factor}_PCTL"]})
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        column_config={
            "pctl": st.column_config.ProgressColumn(
                "league pctl", min_value=0, max_value=100, format="%.0f"
            )
        },
    )

st.divider()

# ---- Playmaking & rebounding --------------------------------------------------
st.subheader("🤝 Playmaking & Rebounding")
playmaking = league_playmaking_rebounding(database, season)
team_pmr = playmaking.loc[playmaking["TEAM_ID"] == team_id].iloc[0]

pmr_cols = st.columns(6)
for col, (label, column, fmt) in zip(
    pmr_cols,
    (
        ("AST%", "AST_PCT", "{:.1%}"),
        ("AST/TO", "AST_TO", "{:.2f}"),
        ("AST ratio", "AST_RATIO", "{:.1f}"),
        ("OREB%", "OREB_PCT", "{:.1%}"),
        ("DREB%", "DREB_PCT", "{:.1%}"),
        ("REB%", "REB_PCT", "{:.1%}"),
    ),
    strict=True,
):
    col.metric(
        label,
        fmt.format(team_pmr[column]),
        f"{team_pmr[f'{column}_PCTL']:.0f}th pctl",
        delta_color="off",
    )

ast_col, reb_col = st.columns(2)
with ast_col:
    st.markdown("**Assist leaders**")
    st.dataframe(
        database.query_df(
            "SELECT PLAYER_NAME, AST, AST_PCT, AST_TO FROM player_season_full "
            "WHERE TEAM_ID = ? AND season = ? AND MIN >= 15 ORDER BY AST DESC LIMIT 5",
            [team_id, season],
        ),
        hide_index=True,
        use_container_width=True,
    )
with reb_col:
    st.markdown("**Rebound leaders**")
    st.dataframe(
        database.query_df(
            "SELECT PLAYER_NAME, REB, OREB, DREB, REB_PCT FROM player_season_full "
            "WHERE TEAM_ID = ? AND season = ? AND MIN >= 15 ORDER BY REB DESC LIMIT 5",
            [team_id, season],
        ),
        hide_index=True,
        use_container_width=True,
    )

st.divider()

# ---- Recent form ------------------------------------------------------------
st.subheader("📉 Recent form — rolling 5-game point differential")
games = team_game_factors(database, team_id, season)
games["NET_5G"] = games["PLUS_MINUS"].rolling(5).mean()
fig = px.line(games, x="GAME_DATE", y="NET_5G")
fig.add_hline(y=0, line_dash="dot", line_color=GRID)
fig.update_layout(**plotly_layout(), height=320, xaxis_title="", yaxis_title="Avg +/- (last 5)")
st.plotly_chart(fig, use_container_width=True)
st.caption(f"{len(games)} games · season point differential {games['PLUS_MINUS'].sum():+.0f}.")
