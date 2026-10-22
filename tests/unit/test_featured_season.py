"""The featured (default) season skips a season that has only just started."""

from __future__ import annotations

import pandas as pd

from hoops_lab.analytics.seasons import featured_season
from hoops_lab.storage.database import Database


def _db(games_per_team: dict[str, tuple[int, int]]) -> Database:
    """In-memory ``games`` table with four teams.

    ``games_per_team`` maps a season to (games for teams 1 and 2, games for teams 3 and 4):
    teams 1 and 2 only ever play each other, as do teams 3 and 4.
    """
    rows = []
    for season, (first_pair, second_pair) in games_per_team.items():
        rows += [{"season": season, "home_team_id": 1, "away_team_id": 2}] * first_pair
        rows += [{"season": season, "home_team_id": 3, "away_team_id": 4}] * second_pair
    db = Database(path=":memory:")
    db.connect().register("games", pd.DataFrame(rows))
    return db


def test_the_latest_season_is_featured_once_every_team_has_played_enough() -> None:
    db = _db({"2024-25": (82, 82), "2025-26": (10, 12)})
    assert featured_season(db, min_team_games=10) == "2025-26"


def test_the_previous_season_is_featured_while_any_team_is_below_the_threshold() -> None:
    db = _db({"2024-25": (82, 82), "2025-26": (82, 82), "2026-27": (9, 14)})
    assert featured_season(db, min_team_games=10) == "2025-26"


def test_a_team_that_has_not_played_yet_keeps_the_season_unfeatured() -> None:
    pairs = ((1, 2), (3, 4))
    rows = [{"season": "2025-26", "home_team_id": h, "away_team_id": a} for h, a in pairs] * 82
    # 2026-27: teams 1, 2 and 3 have 12+ games each, team 4 has not played at all.
    rows += [{"season": "2026-27", "home_team_id": 1, "away_team_id": 2}] * 12
    rows += [{"season": "2026-27", "home_team_id": 3, "away_team_id": 2}] * 12
    db = Database(path=":memory:")
    db.connect().register("games", pd.DataFrame(rows))

    assert featured_season(db, min_team_games=10) == "2025-26"


def test_the_newest_season_is_the_fallback_when_none_qualifies() -> None:
    db = _db({"2026-27": (2, 3)})
    assert featured_season(db, min_team_games=10) == "2026-27"


def test_an_unseeded_database_has_no_featured_season() -> None:
    assert featured_season(Database(path=":memory:")) is None


def test_an_empty_database_has_no_featured_season() -> None:
    db = Database(path=":memory:")
    db.connect().register(
        "games", pd.DataFrame({"season": [], "home_team_id": [], "away_team_id": []})
    )
    assert featured_season(db) is None
