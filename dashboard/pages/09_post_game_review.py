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

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.components.data_access import get_database  # noqa: E402
from hoops_lab.features.four_factors import FACTOR_LABELS  # noqa: E402
from hoops_lab.features.possession import sort_chronological  # noqa: E402
from hoops_lab.models.shot_quality_model import train_shot_quality  # noqa: E402
from hoops_lab.models.win_probability import (  # noqa: E402
    build_states_from_db,
    predict_wp_frame,
    train_win_probability,
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
st.title("📝 Post-Game Review")

database = get_database()
if database.table_rows("possessions") == 0:
    st.warning(
        "No possessions built — run `python -m hoops_lab.features.possession` "
        "after the seeder (see README)."
    )
    st.stop()

games = database.query_df(
    """
    SELECT DISTINCT p.game_id, g.season, g.game_date,
           th.abbreviation AS home_abbr, ta.abbreviation AS away_abbr
    FROM possessions AS p
    JOIN games AS g ON g.game_id = p.game_id
    JOIN teams AS th ON th.team_id = g.home_team_id
    JOIN teams AS ta ON ta.team_id = g.away_team_id
    ORDER BY g.game_date DESC
    """
)
labels = [f"{r.away_abbr} @ {r.home_abbr} — {r.game_date} ({r.season})" for r in games.itertuples()]
chosen = st.sidebar.selectbox("Game", labels)
game_id = str(games.iloc[labels.index(chosen)]["game_id"])


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
    wp_model = _wp_model(game_id)
    events = sort_chronological(
        database.query_df("SELECT * FROM play_by_play WHERE gameId = ?", [game_id])
    )
    home_score = pd.to_numeric(events["scoreHome"], errors="coerce")
    away_score = pd.to_numeric(events["scoreAway"], errors="coerce")
    scoring = events.loc[home_score.notna() & away_score.notna()].copy()
    if wp_model is None or scoring.empty:
        st.info("Not enough data for the win probability curve.")
    else:
        from hoops_lab.features.possession import _clock_seconds

        clock_min = _clock_seconds(scoring["clock"]) / 60.0
        period = scoring["period"].astype(int)
        scoring["minutes_remaining"] = ((4 - period.clip(upper=4)) * 12.0 + clock_min).clip(
            lower=0.0
        )
        scoring["margin"] = (home_score.loc[scoring.index] - away_score.loc[scoring.index]).astype(
            float
        )
        scoring["wp_home"] = predict_wp_frame(wp_model, scoring)

        fig = px.line(scoring.reset_index(drop=True), y="wp_home")
        fig.add_hline(y=0.5, line_dash="dot", line_color="#888")
        fig.update_layout(
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
