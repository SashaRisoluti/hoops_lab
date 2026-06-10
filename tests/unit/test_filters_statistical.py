"""Unit tests for dynamic statistical filters and AND/OR groups."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hoops_lab.filters.statistical import StatFilter, StatFilterGroup


def test_comparison_filter_builds_parameterized_sql() -> None:
    fragment, params = StatFilter(field="AST", op=">", value=5).where_sql()
    assert fragment == '"AST" > ?'
    assert params == [5.0]


def test_between_filter_requires_two_values() -> None:
    fragment, params = StatFilter(field="PTS", op="between", value=[20, 30]).where_sql()
    assert fragment == '"PTS" BETWEEN ? AND ?'
    assert params == [20.0, 30.0]

    with pytest.raises(ValidationError):
        StatFilter(field="PTS", op="between", value=[20])


def test_top_n_builds_qualify_fragment() -> None:
    fragment, params = StatFilter(field="PTS", op="top_n", value=10).qualify_sql()
    assert fragment == 'rank() OVER (ORDER BY "PTS" DESC) <= ?'
    assert params == [10]

    with pytest.raises(ValidationError):
        StatFilter(field="PTS", op="top_n", value=0)


def test_percentile_filters_use_percent_rank() -> None:
    fragment, params = StatFilter(field="TS_PCT", op="percentile_above", value=90).qualify_sql()
    assert fragment == 'percent_rank() OVER (ORDER BY "TS_PCT") >= ?'
    assert params == [0.9]

    with pytest.raises(ValidationError):
        StatFilter(field="TS_PCT", op="percentile_above", value=101)


def test_field_names_are_injection_guarded() -> None:
    with pytest.raises(ValidationError):
        StatFilter(field='PTS"; DROP TABLE players; --', op=">", value=1)


def test_group_joins_filters_with_or_logic() -> None:
    group = StatFilterGroup(
        logic="OR",
        filters=[
            StatFilter(field="USG_PCT", op=">", value=30),
            StatFilter(field="PTS", op=">", value=25),
        ],
    )
    fragment, params = group.where_sql()
    assert fragment == '("USG_PCT" > ? OR "PTS" > ?)'
    assert params == [30.0, 25.0]


def test_window_operators_forbidden_in_or_groups() -> None:
    with pytest.raises(ValidationError, match="AND"):
        StatFilterGroup(
            logic="OR",
            filters=[
                StatFilter(field="PTS", op=">", value=25),
                StatFilter(field="PTS", op="top_n", value=10),
            ],
        )
