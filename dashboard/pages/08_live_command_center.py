"""Live Command Center — replay simulation + (in season) real live games.

Replay mode steps through the ingested historical play-by-play with the
exact pipeline a live game would use: events -> GameState -> live KPIs ->
live-vs-season comparison -> tactical alerts. Live mode feeds the same
pipeline from the NBA live feed (stats.nba.com as fallback) and auto-refreshes.
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

from dashboard.components.alert_panel import render_alert_panel  # noqa: E402
from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.live_kpi_strip import render_kpi_strip  # noqa: E402
from dashboard.components.page_header import render_page_header  # noqa: E402
from dashboard.components.search_select import search_select  # noqa: E402
from dashboard.components.shot_chart import render_shot_chart  # noqa: E402
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import (  # noqa: E402
    GRID,
    inject_theme,
    plotly_layout,
    render_command_bar,
)
from hoops_lab.analytics.seasons import featured_season  # noqa: E402
from hoops_lab.config import ENVIRONMENT, LIVE_REFRESH_SECONDS  # noqa: E402
from hoops_lab.features.possession import sort_chronological  # noqa: E402
from hoops_lab.ingestion.live import game_label, pickable_games  # noqa: E402
from hoops_lab.live.alert_engine import evaluate_alerts  # noqa: E402
from hoops_lab.live.game_state import GameState, shot_frame_from_events  # noqa: E402
from hoops_lab.live.live_vs_historical import comparison_table, get_baselines  # noqa: E402
from hoops_lab.live.poller import LivePoller  # noqa: E402
from hoops_lab.models.win_probability import (  # noqa: E402
    build_states_from_db,
    train_win_probability,
    wp_curve,
)

st.set_page_config(page_title="Live Command Center", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Live")
render_page_header("Live Command Center", subtitle="Live KPIs, alerts and win probability")

database = get_database()
if database.table_rows("play_by_play") == 0:
    st.warning("No play-by-play loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)


@st.cache_resource
def _wp_model(excluded_game: str):
    """Win probability model trained on every OTHER sampled game (no leakage)."""
    states = build_states_from_db(database)
    train = states.loc[states["game_id"] != excluded_game]
    return train_win_probability(train) if len(train) else None


def _render_game(
    events: pd.DataFrame,
    home_id: int,
    away_id: int,
    home_abbr: str,
    away_abbr: str,
    season: str,
    game_id: str,
) -> None:
    """Shared pipeline for replay and live: events -> state -> KPIs, comparison, alerts."""
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
                width="stretch",
                column_config=table_config,
            )

    with alerts_col:
        render_alert_panel(evaluate_alerts(state, baselines))

    st.divider()

    # ---- Win probability + shot map ----------------------------------------------
    wp_col, shotmap_col = st.columns(2)

    with wp_col:
        st.subheader(f"📈 Win probability — {home_abbr}")
        wp_model = _wp_model(game_id)
        curve = wp_curve(wp_model, events) if wp_model is not None else None
        if curve is None or curve.empty:
            st.info("Waiting for the first scoring update.")
        else:
            fig = px.line(curve.reset_index(drop=True), y="wp_home")
            fig.add_hline(y=0.5, line_dash="dot", line_color=GRID)
            fig.update_layout(
                **plotly_layout(),
                height=360,
                yaxis=dict(range=[0, 1], title=f"P({home_abbr} win)"),
                xaxis_title="Scoring events processed",
            )
            st.plotly_chart(fig, width="stretch")
            st.caption(f"Current: {curve['wp_home'].iloc[-1]:.0%} — model excludes this game.")

    with shotmap_col:
        st.subheader("🎯 Shot map — from events")
        shot_frame = shot_frame_from_events(events)
        if shot_frame.empty:
            st.info("No shots with coordinates yet.")
        else:
            side = st.radio("Show", ["Both", home_abbr, away_abbr], horizontal=True)
            if side == home_abbr:
                shot_frame = shot_frame.loc[shot_frame["TEAM_ID"] == home_id]
            elif side == away_abbr:
                shot_frame = shot_frame.loc[shot_frame["TEAM_ID"] == away_id]
            render_shot_chart(shot_frame)
            made = int(shot_frame["SHOT_MADE_FLAG"].sum())
            assisted = int(shot_frame["ASSISTED"].sum())
            if made:
                st.caption(
                    f"{len(shot_frame)} shots · {made} made, {assisted} assisted "
                    f"({assisted / made:.0%} of makes)."
                )

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
        width="stretch",
    )


st.sidebar.header("🔍 Source")
modes = ["Replay simulation"]
if ENVIRONMENT != "production":
    modes.append("Live (nba_api)")
mode = st.sidebar.radio("Mode", modes)

if mode == "Live (nba_api)":
    st.info(
        "Live mode polls the NBA live feed (stats.nba.com as fallback) and runs the same "
        f"pipeline as the replay, refreshing every {LIVE_REFRESH_SECONDS} s. Outside game "
        "hours no games will be listed."
    )
    if "live_poller" not in st.session_state:
        st.session_state.live_poller = LivePoller()
    # Baselines from the featured season: a few early games are noise, not a baseline.
    live_season = featured_season(database)

    @st.fragment(run_every=LIVE_REFRESH_SECONDS)
    def _live_section() -> None:
        """Auto-refreshing live view: scoreboard -> chosen game's events -> shared pipeline."""
        poller = st.session_state.live_poller
        try:
            games = pickable_games(poller.scoreboard())
        except Exception as exc:  # network/availability — degrade gracefully
            st.warning(f"Live scoreboard unavailable: {exc}")
            return
        if not games:
            st.info("No NBA games in progress or finished today — use the replay simulation.")
            return
        game_id = search_select(
            "Live game",
            list(games),
            format_func=lambda gid: game_label(games[gid]),
            key="live_game_pick",
        )
        game = games[game_id]
        try:
            events = poller.events(game_id)
        except Exception as exc:  # network/availability — degrade gracefully
            st.warning(f"Live play-by-play unavailable: {exc}")
            return
        st.caption(f"Source: {poller.source} · updated {poller.updated_at:%H:%M:%S} ET")
        st.button("🔄 Refresh")
        if events.empty:
            st.info("Waiting for the first play-by-play event.")
            return
        _render_game(
            events,
            int(game["homeTeam"]["teamId"]),
            int(game["awayTeam"]["teamId"]),
            game["homeTeam"]["teamTricode"],
            game["awayTeam"]["teamTricode"],
            live_season,
            game_id,
        )

    _live_section()
else:
    # Team and season come from the shared rail.
    replay_games = database.query_df(
        """
        SELECT DISTINCT p.gameId AS game_id, g.season, g.game_date,
               th.abbreviation AS home_abbr, ta.abbreviation AS away_abbr,
               g.home_team_id, g.away_team_id
        FROM play_by_play AS p
        JOIN games AS g ON g.game_id = p.gameId
        JOIN teams AS th ON th.team_id = g.home_team_id
        JOIN teams AS ta ON ta.team_id = g.away_team_id
        WHERE g.season = ? AND (g.home_team_id = ? OR g.away_team_id = ?)
        ORDER BY g.game_date DESC
        """,
        [season, team_id, team_id],
    )
    if replay_games.empty:
        st.info(f"No play-by-play sampled for {team_abbr} in {season}.")
        st.stop()
    labels = [
        f"{r.away_abbr} @ {r.home_abbr} — {r.game_date} ({r.season})"
        for r in replay_games.itertuples()
    ]
    with st.sidebar:
        chosen = search_select("Game", labels, key="replay_game_pick")
    row = replay_games.iloc[labels.index(chosen)]
    home_id, away_id = int(row["home_team_id"]), int(row["away_team_id"])
    home_abbr, away_abbr = row["home_abbr"], row["away_abbr"]
    season = row["season"]
    current_game_id = str(row["game_id"])

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
    _render_game(events, home_id, away_id, home_abbr, away_abbr, season, current_game_id)
