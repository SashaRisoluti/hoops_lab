"""Unit tests for the dynamic query builder.

Half of these tests EXECUTE the generated SQL against an in-memory DuckDB
with small registered tables — proving the queries are valid for the real
engine, not just well-formed strings.
"""

from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from hoops_lab.filters.entity import EntityFilter
from hoops_lab.filters.query_builder import QueryRequest, build_query, run_query
from hoops_lab.filters.statistical import StatFilter, StatFilterGroup
from hoops_lab.filters.temporal import TemporalFilter
from hoops_lab.storage.database import Database


@pytest.fixture()
def db() -> Database:
    """In-memory DuckDB with a season-grain and a game-grain table."""
    database = Database(path=":memory:")
    con = database.connect()

    season_stats = pd.DataFrame(
        {
            "PLAYER_ID": [1, 2, 3, 4],
            "PLAYER_NAME": ["Alpha", "Bravo", "Charlie", "Delta"],
            "TEAM_ID": [100, 100, 200, 200],
            "season": ["2023-24", "2023-24", "2023-24", "2022-23"],
            "GP": [70, 60, 40, 75],
            "MIN": [35.0, 31.0, 20.0, 36.0],
            "PTS": [28.0, 22.0, 15.0, 30.0],
            "AST": [8.0, 4.0, 6.0, 9.0],
        }
    )
    con.register("player_season_stats", season_stats)

    game_log = pd.DataFrame(
        {
            "PLAYER_ID": [1, 1, 1, 2, 2],
            "PLAYER_NAME": ["Alpha", "Alpha", "Alpha", "Bravo", "Bravo"],
            "TEAM_ID": [100] * 5,
            "season": ["2023-24"] * 5,
            "GAME_ID": ["g1", "g2", "g3", "g1", "g2"],
            "GAME_DATE": ["2024-01-01", "2024-01-05", "2024-01-10", "2024-01-01", "2024-01-05"],
            "MATCHUP": ["AAA vs. BBB", "AAA @ CCC", "AAA vs. DDD", "AAA vs. BBB", "AAA @ CCC"],
            "PTS": [20.0, 25.0, 30.0, 10.0, 12.0],
        }
    )
    con.register("box_scores_player", game_log)
    return database


def test_unknown_base_table_is_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(base="players; DROP TABLE players")


def test_unsafe_column_names_are_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(base="player_season", columns=['PTS"; DROP'])


def test_seasons_and_min_sample_filters(db: Database) -> None:
    request = QueryRequest(
        base="player_season",
        columns=["PLAYER_NAME", "PTS"],
        temporal=TemporalFilter(seasons=["2023-24"]),
        entity=EntityFilter(min_minutes=25, min_games=50),
        order_by="PTS",
    )
    result = run_query(db, request)

    # Charlie fails min sample (20 MPG, 40 GP); Delta is another season.
    assert result["PLAYER_NAME"].tolist() == ["Alpha", "Bravo"]


def test_and_group_with_comparison_filters(db: Database) -> None:
    request = QueryRequest(
        base="player_season",
        stats=StatFilterGroup(
            logic="AND",
            filters=[
                StatFilter(field="AST", op=">", value=5),
                StatFilter(field="MIN", op=">=", value=30),
            ],
        ),
    )
    sql, params = build_query(request)
    assert '"AST" > ?' in sql and '"MIN" >= ?' in sql


def test_or_group_execution(db: Database) -> None:
    request = QueryRequest(
        base="player_season",
        columns=["PLAYER_NAME"],
        stats=StatFilterGroup(
            logic="OR",
            filters=[
                StatFilter(field="PTS", op=">", value=27),
                StatFilter(field="AST", op=">", value=5.5),
            ],
        ),
        order_by="PLAYER_NAME",
        descending=False,
    )
    result = run_query(db, request)
    # Alpha (28 pts, 8 ast), Charlie (6 ast), Delta (30 pts, 9 ast).
    assert result["PLAYER_NAME"].tolist() == ["Alpha", "Charlie", "Delta"]


def test_top_n_executes_with_qualify(db: Database) -> None:
    request = QueryRequest(
        base="player_season",
        columns=["PLAYER_NAME", "PTS"],
        stats=StatFilterGroup(filters=[StatFilter(field="PTS", op="top_n", value=2)]),
        order_by="PTS",
    )
    result = run_query(db, request)
    assert result["PLAYER_NAME"].tolist() == ["Delta", "Alpha"]  # 30 and 28 pts


def test_percentile_above_executes(db: Database) -> None:
    request = QueryRequest(
        base="player_season",
        columns=["PLAYER_NAME"],
        stats=StatFilterGroup(filters=[StatFilter(field="PTS", op="percentile_above", value=75)]),
    )
    result = run_query(db, request)
    # percent_rank over [15, 22, 28, 30] -> only the max (Delta) is >= 0.75.
    assert result["PLAYER_NAME"].tolist() == ["Delta"]


def test_limit_is_applied(db: Database) -> None:
    request = QueryRequest(base="player_season", order_by="PTS", limit=1)
    result = run_query(db, request)
    assert len(result) == 1
    assert result["PLAYER_NAME"].iloc[0] == "Delta"


def test_last_n_games_requires_game_grain() -> None:
    with pytest.raises(ValidationError, match="game-grain"):
        QueryRequest(base="player_season", temporal=TemporalFilter(last_n_games=5))


def test_last_n_games_execution(db: Database) -> None:
    request = QueryRequest(
        base="player_game",
        columns=["PLAYER_NAME", "GAME_ID"],
        temporal=TemporalFilter(last_n_games=2),
        order_by="GAME_DATE",
        descending=False,
    )
    result = run_query(db, request)
    # Alpha keeps g2/g3 (last two), Bravo keeps g1/g2 (only two played).
    assert sorted(result["GAME_ID"].tolist()) == ["g1", "g2", "g2", "g3"]
    alpha_games = result.loc[result["PLAYER_NAME"] == "Alpha", "GAME_ID"].tolist()
    assert sorted(alpha_games) == ["g2", "g3"]


def test_home_location_filter_execution(db: Database) -> None:
    from hoops_lab.filters.contextual import ContextualFilter

    request = QueryRequest(
        base="player_game",
        columns=["GAME_ID", "PLAYER_NAME"],
        contextual=ContextualFilter(location="home"),
    )
    result = run_query(db, request)
    assert set(result["GAME_ID"]) == {"g1", "g3"}


def test_date_range_execution(db: Database) -> None:
    request = QueryRequest(
        base="player_game",
        columns=["GAME_ID"],
        temporal=TemporalFilter(date_from="2024-01-04", date_to="2024-01-06"),
    )
    result = run_query(db, request)
    assert set(result["GAME_ID"]) == {"g2"}
