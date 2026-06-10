"""Sidebar with temporal, entity and statistical filters for the explorer.

The widget layer is deliberately thin: every widget value funnels into
:func:`build_request`, a pure function returning a validated
:class:`QueryRequest` — unit-testable without any UI.
"""

from __future__ import annotations

import streamlit as st

from hoops_lab.filters.entity import EntityFilter
from hoops_lab.filters.query_builder import QueryRequest
from hoops_lab.filters.statistical import StatFilter, StatFilterGroup
from hoops_lab.filters.temporal import TemporalFilter

#: Fields offered by the dynamic statistical-filter builder (player_season_full view).
FILTERABLE_FIELDS = [
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "MIN",
    "GP",
    "FGA",
    "FG_PCT",
    "FG3M",
    "FG3A",
    "FG3_PCT",
    "FT_PCT",
    "TS_PCT",
    "EFG_PCT",
    "USG_PCT",
    "AST_PCT",
    "AST_TO",
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "PIE",
    "PLUS_MINUS",
]

OPERATORS = [
    ">",
    ">=",
    "<",
    "<=",
    "=",
    "!=",
    "between",
    "top_n",
    "percentile_above",
    "percentile_below",
]

StatRow = tuple[str, str, float | list[float]]


def build_request(
    seasons: list[str],
    min_minutes: float,
    min_games: int,
    stat_rows: list[StatRow],
    logic: str = "AND",
    order_by: str | None = "PTS",
) -> QueryRequest:
    """Assemble the explorer's QueryRequest from plain values (pure function).

    Raises ``pydantic.ValidationError`` on inconsistent filters — the page
    shows the message instead of running a wrong query.
    """
    stats = None
    if stat_rows:
        stats = StatFilterGroup(
            logic=logic,
            filters=[StatFilter(field=field, op=op, value=value) for field, op, value in stat_rows],
        )
    return QueryRequest(
        base="player_season_full",
        temporal=TemporalFilter(seasons=seasons or None),
        entity=EntityFilter(min_minutes=min_minutes, min_games=min_games),
        stats=stats,
        order_by=order_by,
    )


def _default_row() -> dict:
    return {"field": "AST", "op": ">", "value": 5.0, "value2": 10.0}


def render_filters_sidebar(season_options: list[str]) -> QueryRequest:
    """Render every filter widget and return the resulting QueryRequest."""
    st.sidebar.header("🔍 Filters")

    seasons = st.sidebar.multiselect("Seasons", season_options, default=season_options)

    st.sidebar.subheader("Minimum sample")
    min_minutes = st.sidebar.slider("Min minutes per game", 0.0, 40.0, 25.0, 1.0)
    min_games = st.sidebar.slider("Min games played", 0, 82, 50, 1)

    st.sidebar.subheader("Statistical filters")
    if "stat_rows" not in st.session_state:
        st.session_state.stat_rows = [_default_row()]

    logic = st.sidebar.radio("Combine filters with", ["AND", "OR"], horizontal=True)

    rows: list[StatRow] = []
    for i, row in enumerate(st.session_state.stat_rows):
        columns = st.sidebar.columns([3, 3, 3, 1])
        row["field"] = columns[0].selectbox(
            "Stat", FILTERABLE_FIELDS, index=FILTERABLE_FIELDS.index(row["field"]), key=f"field{i}"
        )
        row["op"] = columns[1].selectbox(
            "Op", OPERATORS, index=OPERATORS.index(row["op"]), key=f"op{i}"
        )
        row["value"] = columns[2].number_input("Value", value=float(row["value"]), key=f"val{i}")
        if row["op"] == "between":
            row["value2"] = st.sidebar.number_input(
                "… and", value=float(row.get("value2", row["value"])), key=f"val2{i}"
            )
            value: float | list[float] = [row["value"], row["value2"]]
        else:
            value = row["value"]
        if columns[3].button("✖", key=f"del{i}", help="Remove this filter"):
            st.session_state.stat_rows.pop(i)
            st.rerun()
        rows.append((row["field"], row["op"], value))

    if st.sidebar.button("➕ Add filter"):
        st.session_state.stat_rows.append(_default_row())
        st.rerun()

    st.sidebar.subheader("Sorting")
    order_by = st.sidebar.selectbox("Order by", FILTERABLE_FIELDS, index=0)

    return build_request(seasons, min_minutes, min_games, rows, logic=logic, order_by=order_by)
