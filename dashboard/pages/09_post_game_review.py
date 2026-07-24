"""Post-Game Review — the automated report for any ingested game.

Models are trained EXCLUDING the selected game (no leakage): the shot
quality model on every other tracked shot, the win probability model on
every other sampled game.
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
)
from dashboard.components.page_header import render_page_header  # noqa: E402
from dashboard.components.search_select import search_select  # noqa: E402
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import (  # noqa: E402
    GRID,
    inject_theme,
    plotly_layout,
    render_command_bar,
)
from hoops_lab.features.four_factors import FACTOR_LABELS  # noqa: E402
from hoops_lab.features.possession import sort_chronological  # noqa: E402
from hoops_lab.models.shot_quality_model import train_shot_quality  # noqa: E402
from hoops_lab.models.win_probability import (  # noqa: E402
    build_states_from_db,
    train_win_probability,
    wp_curve,
)
from hoops_lab.reports.post_game import (  # noqa: E402
    game_four_factors,
    game_header,
    game_runs,
    generate_insights,
    shot_quality_summary,
    top_players,
)

st.set_page_config(page_title="Post-Game Review", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Reports")
render_page_header(
    "Post-Game Review", subtitle="Full-game story: score, factors and win probability"
)

database = get_database()
if database.table_rows("games") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)

st.sidebar.header("🔍 Selection")
games = database.query_df(
    """
    SELECT g.game_id, g.season, g.game_date,
           th.abbreviation AS home_abbr, ta.abbreviation AS away_abbr,
           (pp.game_id IS NOT NULL) AS has_pbp
    FROM games AS g
    JOIN teams AS th ON th.team_id = g.home_team_id
    JOIN teams AS ta ON ta.team_id = g.away_team_id
    LEFT JOIN (SELECT DISTINCT game_id FROM possessions) AS pp ON pp.game_id = g.game_id
    WHERE g.season = ? AND (g.home_team_id = ? OR g.away_team_id = ?)
    ORDER BY g.game_date DESC
    """,
    [season, team_id, team_id],
)
labels = [
    f"{'📊 ' if r.has_pbp else ''}{r.away_abbr} @ {r.home_abbr} — {r.game_date} ({r.season})"
    for r in games.itertuples()
]
with st.sidebar:
    chosen = search_select("Game (📊 = play-by-play available)", labels, key="review_game_pick")
selected_game = games.iloc[labels.index(chosen)]
game_id = str(selected_game["game_id"])
has_pbp = bool(selected_game["has_pbp"])


@st.cache_resource
def _shot_model(excluded_game: str):
    shots = database.query_df("SELECT * FROM shots WHERE GAME_ID != ?", [excluded_game])
    return train_shot_quality(shots) if len(shots) else None


@st.cache_resource
def _wp_model(excluded_game: str):
    states = build_states_from_db(database)
    train = states.loc[states["game_id"] != excluded_game]
    return train_win_probability(train) if len(train) else None


header = game_header(database, game_id)
factors = game_four_factors(database, game_id)
runs = game_runs(database, game_id)
shots = shot_quality_summary(database, game_id, _shot_model(game_id))
teams_by_id = {
    int(header["home_team_id"]): header["home_abbr"],
    int(header["away_team_id"]): header["away_abbr"],
}

# ---- Header + insights -------------------------------------------------------
st.subheader(
    f"{header['away_abbr']} {int(header['away_pts'])} — "
    f"{int(header['home_pts'])} {header['home_abbr']}"
)
st.caption(f"{header['game_date']} · {header['season']} · game {game_id}")
if not has_pbp:
    st.info(
        "Scoring runs and the win probability curve need play-by-play, which was "
        "not sampled for this game — extend coverage with "
        "`HistoricalDownloader.download_play_by_play`."
    )

st.subheader("💡 Auto insights")
for bullet in generate_insights(header, factors, runs, shots, teams_by_id):
    st.markdown(f"- {bullet}")

st.divider()

# ---- Four Factors + win probability ------------------------------------------
factors_col, wp_col = st.columns(2)

with factors_col:
    st.subheader("Four Factors")
    table = factors[["TEAM_ABBREVIATION", "PTS", *FACTOR_LABELS]].rename(
        columns={"TEAM_ABBREVIATION": "team"}
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

with wp_col:
    st.subheader("Win probability — home team")
    events = sort_chronological(
        database.query_df("SELECT * FROM play_by_play WHERE gameId = ?", [game_id])
    )
    wp_model = _wp_model(game_id) if len(events) else None
    scoring = wp_curve(wp_model, events) if wp_model is not None else events.iloc[0:0]
    if scoring.empty:
        st.info("Not enough data for the win probability curve.")
    else:
        fig = px.line(scoring.reset_index(drop=True), y="wp_home")
        fig.add_hline(y=0.5, line_dash="dot", line_color=GRID)
        fig.update_layout(
            **plotly_layout(),
            height=320,
            yaxis=dict(range=[0, 1], title="P(home win)"),
            xaxis_title="Scoring events",
        )
        st.plotly_chart(fig, use_container_width=True)

        swings = scoring["wp_home"].diff().abs()
        if swings.notna().any():
            key_event = scoring.loc[swings.idxmax()]
            st.caption(
                f"Biggest swing ({swings.max():+.1%}): {key_event['description']} "
                f"(Q{int(key_event['period'])})."
            )

st.divider()

# ---- Runs + shot quality + box ------------------------------------------------
runs_col, shots_col = st.columns(2)

with runs_col:
    st.subheader("📈 Scoring runs")
    if runs.empty:
        st.info("No one-sided runs detected (8+ swing over 8 possessions).")
    else:
        display = runs.copy()
        display["team"] = display["team_id"].map(teams_by_id)
        st.dataframe(
            display[["team", "points_for", "points_against", "start_possession", "end_possession"]],
            hide_index=True,
            use_container_width=True,
        )

with shots_col:
    st.subheader("🎯 Shot quality (tracked team)")
    if shots is None:
        st.info("No shot-location data for this game's teams.")
    else:
        cols = st.columns(3)
        cols[0].metric("Shots", shots["attempts"])
        cols[1].metric("Actual pts", f"{shots['actual_pts']:.0f}")
        gap = shots["actual_pts"] - shots["expected_pts"]
        cols[2].metric(
            "Expected pts", f"{shots['expected_pts']:.1f}", f"{gap:+.1f}", delta_color="normal"
        )
        st.dataframe(
            shots["by_player"].head(6),
            hide_index=True,
            use_container_width=True,
            column_config={
                "expected": st.column_config.NumberColumn(format="%.1f"),
                "above_expected": st.column_config.NumberColumn(format="%+.1f"),
            },
        )

st.subheader("⭐ Top performers")
st.dataframe(top_players(database, game_id), hide_index=True, use_container_width=True)
