"""Player Analyzer — player card, percentile radar, advanced stats, on/off.

Percentiles always refer to the filtered population set in the sidebar
(season + minimum sample). The on/off impact is plus/minus-based, computed
from the complete per-team 5-man lineup population.
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.radar_chart import render_radar_chart  # noqa: E402
from dashboard.components.theme import inject_theme, render_command_bar  # noqa: E402
from hoops_lab.analytics.player_profile import player_on_off, radar_percentiles  # noqa: E402
from hoops_lab.features.percentiles import percentile_rank  # noqa: E402
from hoops_lab.filters.entity import EntityFilter  # noqa: E402
from hoops_lab.filters.query_builder import QueryRequest, run_query  # noqa: E402
from hoops_lab.filters.temporal import TemporalFilter  # noqa: E402

HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

#: Card metrics: label -> (column, format, higher_is_better).
CARD_METRICS: dict[str, tuple[str, str, bool]] = {
    "PPG": ("PTS", "{:.1f}", True),
    "REB": ("REB", "{:.1f}", True),
    "AST": ("AST", "{:.1f}", True),
    "TS%": ("TS_PCT", "{:.1%}", True),
    "USG%": ("USG_PCT", "{:.1%}", True),
    "Net Rating": ("NET_RATING", "{:+.1f}", True),
}

st.set_page_config(page_title="Player Analyzer", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Players")
st.title("🧬 Player Analyzer")

database = get_database()

if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

season_options = database.query_df("SELECT season FROM seasons ORDER BY season DESC")[
    "season"
].tolist()

st.sidebar.header("🔍 Comparison population")
season = st.sidebar.selectbox("Season", season_options)
min_minutes = st.sidebar.slider("Min minutes per game", 0.0, 40.0, 15.0, 1.0)
min_games = st.sidebar.slider("Min games played", 0, 82, 30, 1)
st.sidebar.caption("Every percentile on this page refers to this population.")

population = run_query(
    database,
    QueryRequest(
        base="player_season_full",
        temporal=TemporalFilter(seasons=[season]),
        entity=EntityFilter(min_minutes=min_minutes, min_games=min_games),
        order_by="PTS",
    ),
).reset_index(drop=True)

if population.empty:
    st.info("No players match the current population filters.")
    st.stop()

player_name = st.selectbox("Player", population["PLAYER_NAME"].tolist())
row_idx = int(population.index[population["PLAYER_NAME"] == player_name][0])
player = population.iloc[row_idx]

# ---- Player card -----------------------------------------------------------
photo_col, info_col = st.columns([1, 4])
photo_col.image(HEADSHOT_URL.format(player_id=int(player["PLAYER_ID"])), width=180)
info_col.subheader(f"{player['PLAYER_NAME']} — {player['TEAM_ABBREVIATION']}")
info_col.caption(
    f"Season {season} · {int(player['GP'])} games · {player['MIN']:.1f} MPG · "
    f"age {int(player['AGE'])} · population n = {len(population)}"
)

metric_cols = info_col.columns(len(CARD_METRICS))
for col, (label, (column, fmt, higher)) in zip(metric_cols, CARD_METRICS.items(), strict=True):
    value = player[column]
    if pd.isna(value):
        col.metric(label, "—")
        continue
    series = population[column] if higher else -population[column]
    pctl = percentile_rank(series).iloc[row_idx]
    col.metric(label, fmt.format(value), delta=f"{pctl:.0f}th pctl", delta_color="off")

st.divider()

# ---- Radar + on/off --------------------------------------------------------
radar_col, impact_col = st.columns([3, 2])

with radar_col:
    st.subheader("📡 Percentile radar")
    render_radar_chart(radar_percentiles(population, row_idx))
    st.caption(
        "Percentiles vs the filtered population; lower-is-better stats "
        "(defensive rating) are inverted so 100 is always best."
    )

with impact_col:
    st.subheader("🔁 On/Off impact")
    on_off = player_on_off(database, int(player["PLAYER_ID"]), int(player["TEAM_ID"]), season)
    if on_off is None:
        st.info("Not enough lineup minutes to compute on/off for this player-season.")
    else:
        st.metric("Team +/- per 48' (ON court)", f"{on_off['on_pm_per48']:+.1f}")
        st.metric("Team +/- per 48' (OFF court)", f"{on_off['off_pm_per48']:+.1f}")
        st.metric("ON − OFF", f"{on_off['on_off_per48']:+.1f}")
        st.caption(
            f"ON: {on_off['on_min']:.0f}' ({on_off['on_pm']:+.0f}) · "
            f"OFF: {on_off['off_min']:.0f}' ({on_off['off_pm']:+.0f}). "
            "Plus/minus-based, from the complete 5-man lineup population "
            "(per-team queries, no server cap)."
        )

st.divider()

# ---- Full season line ------------------------------------------------------
with st.expander("Full season line (base + advanced)"):
    st.dataframe(population.iloc[[row_idx]], hide_index=True, use_container_width=True)
