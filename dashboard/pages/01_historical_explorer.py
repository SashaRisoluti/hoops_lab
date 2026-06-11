"""Historical Stats Explorer — the Phase 1 main page.

Target flow (spec section 18.2): pick seasons → set the minimum sample →
add dynamic statistical filters → choose the columns → inspect the table →
select a player and a stat → read the percentile histogram.
"""

import sys
from pathlib import Path

# Make the repo root importable regardless of how streamlit was launched.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from dashboard.components.data_access import get_database  # noqa: E402
from dashboard.components.filters_sidebar import render_filters_sidebar  # noqa: E402
from dashboard.components.percentile_histogram import render_percentile_histogram  # noqa: E402
from dashboard.components.stats_table import render_stats_table  # noqa: E402
from dashboard.components.team_rail import render_team_rail  # noqa: E402
from dashboard.components.theme import inject_theme, render_command_bar  # noqa: E402
from hoops_lab.filters.query_builder import run_query  # noqa: E402

st.set_page_config(page_title="Historical Stats Explorer", page_icon="🏀", layout="wide")
inject_theme()
render_command_bar("Explorer")
st.title("📊 Historical Stats Explorer")

database = get_database()

if database.table_rows("seasons") == 0:
    st.warning("No data loaded — run the downloader and the seeder first (see README).")
    st.stop()

team_id, team_abbr, season = render_team_rail(database)

season_options = database.query_df("SELECT season FROM seasons ORDER BY season")["season"].tolist()

try:
    request = render_filters_sidebar(season_options)
except ValidationError as exc:
    st.error(f"Invalid filter combination:\n\n{exc}")
    st.stop()

if st.sidebar.checkbox(f"Limit to {team_abbr} (rail team)", value=False):
    request = request.model_copy(
        update={"entity": request.entity.model_copy(update={"team_ids": [team_id]})}
    )

with st.spinner("Querying DuckDB…"):
    results = run_query(database, request)

st.caption(
    f"**{len(results)}** player-season rows match the filters — this is the population "
    "all percentiles below refer to."
)

if results.empty:
    st.info("No players match the current filters. Loosen them in the sidebar.")
    st.stop()

selected_stats = render_stats_table(results)
st.divider()
render_percentile_histogram(results, selected_stats)
