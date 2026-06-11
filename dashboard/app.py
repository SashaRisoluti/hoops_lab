"""Hoops Lab — Overview dashboard (Claude Design handoff v2, Option B rail).

Dark broadcast layout in NBA tricolor with a fixed data-color language
(orange = good, blue = mid, red = weak), a 30-team rail switcher and a
team-accent band. All numbers are real: ratings/percentiles from the
advanced team stats, factors from the opponent self-join, shots from the
league-wide shot charts, win probability from the PBP sample.
"""

import sys
from pathlib import Path

# Ensure the repo root is importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components import overview_cards as cards  # noqa: E402
from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.shot_chart import render_shot_chart  # noqa: E402
from dashboard.components.team_rail import logo_url, render_team_rail  # noqa: E402
from dashboard.components.theme import (  # noqa: E402
    ORANGE,
    TEAM_ACCENTS,
    TEXT_FAINT,
    inject_theme,
    render_command_bar,
)
from hoops_lab.analytics.overview import (  # noqa: E402
    conference_standing,
    overview_flags,
    zone_bucket,
)
from hoops_lab.analytics.team_identity import league_team_factors, team_game_factors  # noqa: E402
from hoops_lab.features.percentiles import percentile_rank  # noqa: E402
from hoops_lab.features.possession import sort_chronological  # noqa: E402
from hoops_lab.models.win_probability import (  # noqa: E402
    build_states_from_db,
    train_win_probability,
    wp_curve,
)

st.set_page_config(
    page_title="Hoops Lab — Overview",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()
render_command_bar("Overview")

database = get_database()
if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

teams = database.query_df("SELECT team_id, full_name, abbreviation FROM teams ORDER BY full_name")
id_to_name = dict(zip(teams["team_id"], teams["full_name"], strict=True))

# ---- Team rail (Option B, shared shell) ----------------------------------------
team_id, selected_abbr, season = render_team_rail(database)
accent = TEAM_ACCENTS.get(selected_abbr, ORANGE)
team_name = id_to_name[team_id]

# ---- Data assembly ------------------------------------------------------------
advanced = database.query_df("SELECT * FROM advanced_team_stats WHERE season = ?", [season])
for column, invert in (
    ("OFF_RATING", False),
    ("DEF_RATING", True),
    ("NET_RATING", False),
    ("PACE", False),
    ("TS_PCT", False),
):
    series = -advanced[column] if invert else advanced[column]
    advanced[f"{column}_PCTL"] = percentile_rank(series)
team_adv = advanced.loc[advanced["TEAM_ID"] == team_id].iloc[0]

games = team_game_factors(database, team_id, season)
home_ids = set(
    database.query_df(
        "SELECT game_id FROM games WHERE season = ? AND home_team_id = ?", [season, team_id]
    )["game_id"]
)
games["is_home"] = games["GAME_ID"].isin(home_ids)

rank, conference = conference_standing(advanced, teams, team_id)
suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank if rank < 20 else rank % 10, "th")
last = games.iloc[-1]
last_game = (
    f"{'vs' if last['is_home'] else '@'} {last['OPP_ABBREVIATION']} · "
    f"{last['WL']} {last['PLUS_MINUS']:+.0f}"
)
st.markdown(
    cards.team_band(
        accent=accent,
        name=team_name,
        subtitle=(
            f"{int(team_adv['W'])}–{int(team_adv['L'])} · {rank}{suffix} {conference.title()}ern "
            f"Conference · Net {team_adv['NET_RATING']:+.1f}"
        ),
        last5=games["WL"].tail(5).tolist(),
        last_game=last_game,
        abbr=selected_abbr,
        logo=logo_url(team_id),
    ),
    unsafe_allow_html=True,
)

# ---- KPI strip -----------------------------------------------------------------
kpis = st.columns(5)
kpi_specs = [
    ("OFF RATING", f"{team_adv['OFF_RATING']:.1f}", team_adv["OFF_RATING_PCTL"], None),
    ("DEF RATING", f"{team_adv['DEF_RATING']:.1f}", team_adv["DEF_RATING_PCTL"], None),
    ("NET RATING", f"{team_adv['NET_RATING']:+.1f}", team_adv["NET_RATING_PCTL"], ORANGE),
    ("PACE", f"{team_adv['PACE']:.1f}", team_adv["PACE_PCTL"], None),
    ("TS%", f"{team_adv['TS_PCT'] * 100:.1f}", team_adv["TS_PCT_PCTL"], None),
]
for col, (label, value, pctl, color) in zip(kpis, kpi_specs, strict=True):
    col.markdown(cards.kpi_card(label, value, float(pctl), color), unsafe_allow_html=True)

# ---- Row A: radar / shot map / WP + flags ---------------------------------------
league = league_team_factors(database, season)
team_factors = league.loc[league["TEAM_ID"] == team_id].iloc[0]

row_a = st.columns(3)
with row_a[0]:
    st.markdown(cards.card_title("Four Factors Radar", "league pctl"), unsafe_allow_html=True)
    radar_axes = {
        "eFG%": "OFF_EFG",
        "Ball sec": "OFF_TOV_PCT",
        "Off glass": "OFF_ORB_PCT",
        "FT rate": "OFF_FT_RATE",
        "Shot def": "DEF_EFG",
        "Forced TOV": "DEF_TOV_PCT",
        "Def glass": "DEF_ORB_PCT",
        "Foul disc": "DEF_FT_RATE",
    }
    st.plotly_chart(
        cards.radar_figure(
            {label: float(team_factors[f"{f}_PCTL"]) for label, f in radar_axes.items()}
        ),
        use_container_width=True,
    )
    st.caption("Offense + defense — percentile vs all 30 teams.")

with row_a[1]:
    st.markdown(cards.card_title("Shot Map", f"{season}"), unsafe_allow_html=True)
    shots = database.query_df(
        "SELECT * FROM shots WHERE season = ? AND TEAM_ID = ?", [season, team_id]
    )
    if shots.empty:
        st.info("No shot-location data for this team yet.")
    else:
        render_shot_chart(shots)
        shots["bucket"] = shots["SHOT_ZONE_BASIC"].map(zone_bucket)
        tiles = st.columns(4)
        for col, bucket in zip(tiles, ("RIM", "MID", "CORNER 3", "ABOVE BREAK 3"), strict=True):
            zone = shots.loc[shots["bucket"] == bucket, "SHOT_MADE_FLAG"]
            fg = float(zone.mean()) if len(zone) else 0.0
            col.markdown(cards.zone_tile(bucket, fg, "3" in bucket), unsafe_allow_html=True)

with row_a[2]:

    @st.cache_resource
    def _wp_model(excluded_game: str):
        states = build_states_from_db(database)
        train = states.loc[states["game_id"] != excluded_game]
        return train_win_probability(train) if len(train) else None

    wp_games = database.query_df(
        """
        SELECT g.game_id, g.home_team_id FROM games AS g
        JOIN (SELECT DISTINCT game_id FROM possessions) AS p ON p.game_id = g.game_id
        WHERE g.season = ? AND (g.home_team_id = ? OR g.away_team_id = ?)
        ORDER BY g.game_date DESC LIMIT 1
        """,
        [season, team_id, team_id],
    )
    st.markdown(cards.card_title("Win Probability — Last Game"), unsafe_allow_html=True)
    if wp_games.empty:
        st.info("No play-by-play sampled for this team/season yet.")
    else:
        wp_game_id = str(wp_games.iloc[0]["game_id"])
        events = sort_chronological(
            database.query_df("SELECT * FROM play_by_play WHERE gameId = ?", [wp_game_id])
        )
        model = _wp_model(wp_game_id)
        curve = wp_curve(model, events) if model is not None else events.iloc[0:0]
        if curve.empty:
            st.info("Not enough scoring events for the curve.")
        else:
            if int(wp_games.iloc[0]["home_team_id"]) != team_id:
                curve = curve.assign(wp_home=1.0 - curve["wp_home"])  # team perspective
            st.plotly_chart(cards.wp_figure(curve), use_container_width=True)

    st.markdown(cards.card_title("Tactical Flags"), unsafe_allow_html=True)
    flags_html = "".join(
        cards.flag_box(flag["severity"], flag["message"]) for flag in overview_flags(games)
    )
    st.markdown(flags_html, unsafe_allow_html=True)

# ---- Row B: factors detail / leaders / form -------------------------------------
row_b = st.columns(3)
with row_b[0]:
    st.markdown(
        cards.card_title("Four Factors Detail", "value · league pctl"), unsafe_allow_html=True
    )
    offense = [
        ("eFG%", f"{team_factors['OFF_EFG']:.1%}", float(team_factors["OFF_EFG_PCTL"])),
        ("TOV%", f"{team_factors['OFF_TOV_PCT']:.1f}%", float(team_factors["OFF_TOV_PCT_PCTL"])),
        ("OREB%", f"{team_factors['OFF_ORB_PCT']:.1f}%", float(team_factors["OFF_ORB_PCT_PCTL"])),
        ("FT rate", f"{team_factors['OFF_FT_RATE']:.3f}", float(team_factors["OFF_FT_RATE_PCTL"])),
    ]
    defense = [
        ("Opp eFG%", f"{team_factors['DEF_EFG']:.1%}", float(team_factors["DEF_EFG_PCTL"])),
        (
            "Forced TOV",
            f"{team_factors['DEF_TOV_PCT']:.1f}%",
            float(team_factors["DEF_TOV_PCT_PCTL"]),
        ),
        (
            "Def glass",
            f"{100 - team_factors['DEF_ORB_PCT']:.1f}%",
            float(team_factors["DEF_ORB_PCT_PCTL"]),
        ),
        (
            "Foul disc",
            f"{team_factors['DEF_FT_RATE']:.3f}",
            float(team_factors["DEF_FT_RATE_PCTL"]),
        ),
    ]
    st.markdown(cards.factor_rows(offense), unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-family:ui-monospace,monospace;font-size:9px;letter-spacing:0.12em;'
        f'color:{TEXT_FAINT};margin:6px 0;">DEFENSE</div>',
        unsafe_allow_html=True,
    )
    st.markdown(cards.factor_rows(defense), unsafe_allow_html=True)
    st.markdown(cards.tricolor_legend(), unsafe_allow_html=True)

with row_b[1]:
    st.markdown(cards.card_title("Team Leaders", "per game"), unsafe_allow_html=True)
    for eyebrow, column, color in (
        ("ASSISTS / GM", "AST", "#2E5FB7"),
        ("REBOUNDS / GM", "REB", ORANGE),
        ("POINTS / GM", "PTS", "#D2243C"),
    ):
        leaders = database.query_df(
            f"SELECT PLAYER_NAME, {column} FROM player_season_full "
            "WHERE TEAM_ID = ? AND season = ? AND MIN >= 15 "
            f"ORDER BY {column} DESC LIMIT 3",
            [team_id, season],
        )
        st.markdown(
            f'<div style="font-family:ui-monospace,monospace;font-size:9px;letter-spacing:0.12em;'
            f'color:{TEXT_FAINT};margin:6px 0 4px;">{eyebrow}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            cards.leader_rows(
                list(zip(leaders["PLAYER_NAME"], leaders[column], strict=True)), color
            ),
            unsafe_allow_html=True,
        )

with row_b[2]:
    last10 = games.tail(10)
    wins10 = int((last10["WL"] == "W").sum())
    st.markdown(
        cards.card_title(
            "Recent Form — Last 10",
            f"{wins10}–{10 - wins10} · {last10['PLUS_MINUS'].mean():+.1f} avg",
        ),
        unsafe_allow_html=True,
    )
    st.plotly_chart(cards.form_figure(last10), use_container_width=True)

    poss = (last10["FGA"] + 0.44 * last10["FTA"] - last10["OREB"] + last10["TOV"]).sum()
    net100 = last10["PLUS_MINUS"].sum() / poss * 100.0 if poss else 0.0
    home_w = int(((games["is_home"]) & (games["WL"] == "W")).sum())
    home_l = int(((games["is_home"]) & (games["WL"] == "L")).sum())
    road_w = int(((~games["is_home"]) & (games["WL"] == "W")).sum())
    road_l = int(((~games["is_home"]) & (games["WL"] == "L")).sum())
    tiles = st.columns(3)
    tiles[0].markdown(
        cards.stat_tile("NET / 100 L10", f"{net100:+.1f}", ORANGE if net100 > 0 else "#E25A6E"),
        unsafe_allow_html=True,
    )
    tiles[1].markdown(cards.stat_tile("HOME", f"{home_w}–{home_l}"), unsafe_allow_html=True)
    tiles[2].markdown(cards.stat_tile("ROAD", f"{road_w}–{road_l}"), unsafe_allow_html=True)
