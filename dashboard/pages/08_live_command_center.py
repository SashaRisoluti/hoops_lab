"""Live Command Center — replay simulation + (in season) real live games.

Replay mode steps through the ingested historical play-by-play with the
exact pipeline a live game would use: events -> GameState -> live KPIs ->
live-vs-season comparison -> tactical alerts. Live mode adapts the nba_api
live feed to the same contract.
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components.alert_panel import render_alert_panel  # noqa: E402
from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.live_kpi_strip import render_kpi_strip  # noqa: E402
from hoops_lab.config import ENVIRONMENT  # noqa: E402
from hoops_lab.features.possession import sort_chronological  # noqa: E402
from hoops_lab.live.alert_engine import evaluate_alerts  # noqa: E402
from hoops_lab.live.game_state import GameState  # noqa: E402
from hoops_lab.live.live_vs_historical import comparison_table, get_baselines  # noqa: E402

st.set_page_config(page_title="Live Command Center", page_icon="🏀", layout="wide")
st.title("📡 Live Command Center")

database = get_database()
if database.table_rows("play_by_play") == 0:
    st.warning("No play-by-play loaded — run the downloader and the seeder first (see README).")
    st.stop()

st.sidebar.header("🔍 Source")
modes = ["Replay simulation"]
if ENVIRONMENT != "production":
    modes.append("Live (nba_api)")
mode = st.sidebar.radio("Mode", modes)

if mode == "Live (nba_api)":
    st.info(
        "Live mode polls the nba_api live endpoints and runs the same pipeline "
        "as the replay. Outside game hours no games will be listed."
    )
    try:
        from hoops_lab.live.poller import LivePoller

        if "live_poller" not in st.session_state:
            st.session_state.live_poller = LivePoller()
        games_today = st.session_state.live_poller.scoreboard()
    except Exception as exc:  # network/availability — degrade gracefully
        st.warning(f"Live scoreboard unavailable: {exc}")
        st.stop()
    in_progress = [g for g in games_today if g.get("gameStatus") == 2]
    if not in_progress:
        st.info("No NBA games in progress right now — use the replay simulation.")
        st.stop()
    labels = {
        f"{g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}": g for g in in_progress
    }
    chosen = st.selectbox("Live game", list(labels))
    game = labels[chosen]
    from hoops_lab.ingestion.live import adapt_live_actions

    events = adapt_live_actions(
        st.session_state.live_poller.play_by_play(game["gameId"]), game_id=game["gameId"]
    )
    home_id = int(game["homeTeam"]["teamId"])
    away_id = int(game["awayTeam"]["teamId"])
    home_abbr = game["homeTeam"]["teamTricode"]
    away_abbr = game["awayTeam"]["teamTricode"]
    season = database.query_df("SELECT max(season) AS s FROM seasons").iloc[0]["s"]
    st.button("🔄 Refresh")
else:
    replay_games = database.query_df(
        """
        SELECT DISTINCT p.gameId AS game_id, g.season, g.game_date,
               th.abbreviation AS home_abbr, ta.abbreviation AS away_abbr,
               g.home_team_id, g.away_team_id
        FROM play_by_play AS p
        JOIN games AS g ON g.game_id = p.gameId
        JOIN teams AS th ON th.team_id = g.home_team_id
        JOIN teams AS ta ON ta.team_id = g.away_team_id
        ORDER BY g.game_date DESC
        """
    )
    labels = [
        f"{r.away_abbr} @ {r.home_abbr} — {r.game_date} ({r.season})"
        for r in replay_games.itertuples()
    ]
    chosen = st.sidebar.selectbox("Game", labels)
    row = replay_games.iloc[labels.index(chosen)]
    home_id, away_id = int(row["home_team_id"]), int(row["away_team_id"])
    home_abbr, away_abbr = row["home_abbr"], row["away_abbr"]
    season = row["season"]

    all_events = sort_chronological(
        database.query_df("SELECT * FROM play_by_play WHERE gameId = ?", [row["game_id"]])
    )
    total = len(all_events)

    if st.session_state.get("replay_game") != row["game_id"]:
        st.session_state.replay_game = row["game_id"]
        st.session_state.replay_cursor = min(150, total)

    controls = st.sidebar.columns(3)
    if controls[0].button("⏩ +10"):
        st.session_state.replay_cursor = min(total, st.session_state.replay_cursor + 10)
    if controls[1].button("⏭ +50"):
        st.session_state.replay_cursor = min(total, st.session_state.replay_cursor + 50)
    if controls[2].button("🔄 Reset"):
        st.session_state.replay_cursor = min(150, total)

    cursor = st.sidebar.slider("Events processed", 20, total, key="replay_cursor")
    events = all_events.iloc[:cursor]

# ---- Shared pipeline: events -> state -> KPIs, comparison, alerts ----------
state = GameState.from_events(events, home_id=home_id, away_id=away_id)
baselines = {
    home_id: get_baselines(database, home_id, season),
    away_id: get_baselines(database, away_id, season),
}

render_kpi_strip(state, home_abbr, away_abbr)
st.divider()

compare_col, alerts_col = st.columns([3, 2])
with compare_col:
    st.subheader("📊 Live vs season")
    table_config = {
        "live": st.column_config.NumberColumn(format="%.3f"),
        "season": st.column_config.NumberColumn(format="%.3f"),
        "delta": st.column_config.NumberColumn(format="%+.3f"),
    }
    for team_id, label in ((home_id, home_abbr), (away_id, away_abbr)):
        st.markdown(f"**{label}**")
        st.dataframe(
            comparison_table(state, team_id, baselines[team_id]),
            hide_index=True,
            use_container_width=True,
            column_config=table_config,
        )

with alerts_col:
    render_alert_panel(evaluate_alerts(state, baselines))

st.divider()
st.subheader("🕒 Timeline — last events")
timeline_cols = [
    c
    for c in ("period", "clock", "teamTricode", "description", "scoreHome", "scoreAway")
    if c in state.last_events.columns
]
st.dataframe(
    state.last_events[timeline_cols].iloc[::-1],
    hide_index=True,
    use_container_width=True,
)
