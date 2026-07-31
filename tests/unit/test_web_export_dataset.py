"""The JSON the web app consumes is built from the same analytics the dashboard uses."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from hoops_lab.storage.database import Database
from scripts.export_web_data import (
    DATA_DIR,
    LEADER_CATEGORIES,
    MIN_GAMES,
    MIN_MINUTES,
    build_index,
    build_leaders,
    build_team_ratings,
    export_dataset,
)


def _db() -> Database:
    """In-memory database with two seasons, three teams and four players."""
    db = Database(path=":memory:")
    con = db.connect()
    con.register(
        "teams",
        pd.DataFrame(
            {
                "team_id": [1610612737, 1610612738, 1610612747],
                "full_name": ["Atlanta Hawks", "Boston Celtics", "Los Angeles Lakers"],
                "abbreviation": ["ATL", "BOS", "LAL"],
            }
        ),
    )
    con.register("seasons", pd.DataFrame({"season": ["2024-25", "2025-26"]}))
    con.register(
        "games",
        pd.DataFrame({"game_id": ["1", "2", "3"], "season": ["2024-25", "2025-26", "2025-26"]}),
    )
    con.register(
        "player_season_full",
        pd.DataFrame(
            {
                "season": ["2025-26"] * 4,
                "PLAYER_ID": [1, 2, 3, 4],
                "PLAYER_NAME": ["Star", "Runner Up", "Bench Guy", "Cameo"],
                "TEAM_ABBREVIATION": ["ATL", "BOS", "LAL", "ATL"],
                "GP": [70, 68, 65, 3],  # Cameo is below MIN_GAMES
                "MIN": [35.0, 33.0, 8.0, 30.0],  # Bench Guy is below MIN_MINUTES
                "PTS": [30.0, 25.0, 22.0, 40.0],
                "AST": [5.0, 9.0, 1.0, 2.0],
                "REB": [7.0, 4.0, 2.0, 1.0],
                "TS_PCT": [0.62, 0.58, 0.70, 0.80],
            }
        ),
    )
    con.register(
        "advanced_team_stats",
        pd.DataFrame(
            {
                "season": ["2025-26"] * 3,
                "TEAM_ID": [1610612737, 1610612738, 1610612747],
                "TEAM_NAME": ["Atlanta Hawks", "Boston Celtics", "Los Angeles Lakers"],
                "W": [50, 45, 40],
                "L": [32, 37, 42],
                "OFF_RATING": [118.0, 115.0, 112.0],
                "DEF_RATING": [110.0, 108.0, 114.0],
                "NET_RATING": [8.0, 7.0, -2.0],
                "PACE": [99.0, 97.5, 101.0],
            }
        ),
    )
    return db


# ---- index ------------------------------------------------------------------


def test_index_lists_the_seasons_newest_first() -> None:
    index = build_index(_db())
    assert index["seasons"] == ["2025-26", "2024-25"]


def test_index_names_the_latest_season() -> None:
    assert build_index(_db())["latestSeason"] == "2025-26"


def test_index_carries_every_team_with_its_readable_accent() -> None:
    from dashboard.components.theme import TEAM_ACCENTS_READABLE

    teams = build_index(_db())["teams"]
    assert [t["tricode"] for t in teams] == ["ATL", "BOS", "LAL"]
    assert teams[0]["accent"] == TEAM_ACCENTS_READABLE["ATL"]


def test_index_summary_counts_the_real_rows() -> None:
    summary = build_index(_db())["summary"]
    assert summary["teams"] == 3
    assert summary["seasons"] == 2
    assert summary["games"] == 3


def test_index_records_when_it_was_generated() -> None:
    stamp = build_index(_db())["generatedAt"]
    datetime.fromisoformat(stamp)  # raises if not ISO 8601


# ---- leaders ----------------------------------------------------------------


def test_leaders_exclude_players_below_the_minimum_games() -> None:
    leaders = build_leaders(_db(), "2025-26")
    points = next(c for c in leaders["categories"] if c["key"] == "PTS")
    names = [entry["name"] for entry in points["leaders"]]
    # Cameo scores the most per game but has played only 3 games.
    assert "Cameo" not in names


def test_leaders_exclude_players_below_the_minimum_minutes() -> None:
    leaders = build_leaders(_db(), "2025-26")
    points = next(c for c in leaders["categories"] if c["key"] == "PTS")
    assert "Bench Guy" not in [entry["name"] for entry in points["leaders"]]


def test_leaders_are_sorted_by_the_category_value() -> None:
    leaders = build_leaders(_db(), "2025-26")
    points = next(c for c in leaders["categories"] if c["key"] == "PTS")
    assert [entry["name"] for entry in points["leaders"]] == ["Star", "Runner Up"]


def test_leaders_rank_each_category_independently() -> None:
    leaders = build_leaders(_db(), "2025-26")
    assists = next(c for c in leaders["categories"] if c["key"] == "AST")
    assert assists["leaders"][0]["name"] == "Runner Up"


def test_leaders_cover_every_configured_category() -> None:
    leaders = build_leaders(_db(), "2025-26")
    assert [c["key"] for c in leaders["categories"]] == [key for key, _ in LEADER_CATEGORIES]


def test_leaders_respect_the_top_n_limit() -> None:
    leaders = build_leaders(_db(), "2025-26", top_n=1)
    points = next(c for c in leaders["categories"] if c["key"] == "PTS")
    assert len(points["leaders"]) == 1


def test_leaders_publish_the_sample_thresholds_they_applied() -> None:
    leaders = build_leaders(_db(), "2025-26")
    assert leaders["minGames"] == MIN_GAMES
    assert leaders["minMinutes"] == MIN_MINUTES


def test_leaders_carry_the_team_tricode_for_colouring() -> None:
    leaders = build_leaders(_db(), "2025-26")
    points = next(c for c in leaders["categories"] if c["key"] == "PTS")
    assert points["leaders"][0]["tricode"] == "ATL"


# ---- team ratings -----------------------------------------------------------


def test_team_ratings_include_every_team() -> None:
    ratings = build_team_ratings(_db(), "2025-26")
    assert len(ratings["teams"]) == 3


def test_team_ratings_attach_the_tricode() -> None:
    ratings = build_team_ratings(_db(), "2025-26")
    assert {t["tricode"] for t in ratings["teams"]} == {"ATL", "BOS", "LAL"}


def test_team_ratings_carry_league_percentiles() -> None:
    ratings = build_team_ratings(_db(), "2025-26")
    best = next(t for t in ratings["teams"] if t["tricode"] == "ATL")
    assert best["netRatingPctl"] == 100.0  # best net rating of the three


def test_defensive_percentile_rewards_the_lower_rating() -> None:
    ratings = build_team_ratings(_db(), "2025-26")
    # BOS has the lowest DEF_RATING, so it must hold the best defensive percentile.
    best_def = max(ratings["teams"], key=lambda t: t["defRatingPctl"])
    assert best_def["tricode"] == "BOS"


# ---- whole export -----------------------------------------------------------


def test_export_writes_the_expected_files(tmp_path: Path) -> None:
    written = export_dataset(_db(), tmp_path, ["2025-26"])
    names = {p.relative_to(tmp_path).as_posix() for p in written}
    assert names == {"index.json", "leaders/2025-26.json", "teams/2025-26.json"}


def test_every_exported_file_is_valid_json(tmp_path: Path) -> None:
    for path in export_dataset(_db(), tmp_path, ["2025-26"]):
        json.loads(path.read_text(encoding="utf-8"))


def test_export_covers_each_requested_season(tmp_path: Path) -> None:
    written = export_dataset(_db(), tmp_path, ["2025-26", "2024-25"])
    names = {p.relative_to(tmp_path).as_posix() for p in written}
    assert "leaders/2024-25.json" in names


def test_data_dir_is_where_the_web_app_reads_from() -> None:
    assert DATA_DIR == "web/public/data"
