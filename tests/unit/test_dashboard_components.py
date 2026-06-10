"""Unit tests for the dashboard components' pure logic (no UI rendering)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dashboard.components.filters_sidebar import build_request
from dashboard.components.stats_table import COLUMN_PRESETS, IDENTITY_COLS
from hoops_lab.filters.query_builder import BASE_TABLES, build_query
from hoops_lab.filters.statistical import SAFE_IDENTIFIER_RE


def test_build_request_combines_all_filters() -> None:
    request = build_request(
        seasons=["2023-24", "2024-25"],
        min_minutes=25,
        min_games=50,
        stat_rows=[("AST", ">", 5.0), ("TS_PCT", "percentile_above", 80)],
        logic="AND",
        order_by="PTS",
    )

    assert request.base == "player_season_full"
    assert request.temporal.seasons == ["2023-24", "2024-25"]
    assert request.entity.min_minutes == 25
    assert request.entity.min_games == 50
    assert request.stats is not None and len(request.stats.filters) == 2

    sql, _ = build_query(request)
    assert "QUALIFY" in sql  # the percentile filter compiles to a window clause


def test_build_request_without_stat_rows() -> None:
    request = build_request(seasons=[], min_minutes=0, min_games=0, stat_rows=[])
    assert request.stats is None
    assert request.temporal.seasons is None  # empty selection means "all seasons"


def test_build_request_surfaces_invalid_filters() -> None:
    with pytest.raises(ValidationError):
        build_request(
            seasons=[],
            min_minutes=0,
            min_games=0,
            stat_rows=[("PTS", "between", [10.0])],  # between needs two values
        )


def test_player_season_full_is_a_registered_base() -> None:
    assert "player_season_full" in BASE_TABLES


def test_column_presets_are_nonempty_and_safe() -> None:
    assert "Box Score" in COLUMN_PRESETS
    for preset, columns in COLUMN_PRESETS.items():
        assert columns, f"preset {preset!r} is empty"
        for column in columns:
            assert SAFE_IDENTIFIER_RE.fullmatch(column), f"{preset}: unsafe {column!r}"
    for column in IDENTITY_COLS:
        assert SAFE_IDENTIFIER_RE.fullmatch(column)
