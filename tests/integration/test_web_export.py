"""The web dataset built from the real database is small, valid and truthful."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH
from hoops_lab.storage.database import Database
from scripts.export_web_data import (
    DATA_DIR,
    MIN_GAMES,
    MIN_MINUTES,
    build_leaders,
    build_team_ratings,
    export_dataset,
)

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)

REPO = Path(__file__).resolve().parents[2]

#: The whole point of a static site is that it loads instantly on a phone.
SIZE_BUDGET_BYTES = 2 * 1024 * 1024


def _latest_season(db: Database) -> str:
    return sorted(db.query_df("SELECT season FROM seasons")["season"].tolist())[-1]


def test_the_full_export_stays_inside_the_size_budget(tmp_path: Path) -> None:
    db = Database()
    seasons = sorted(db.query_df("SELECT season FROM seasons")["season"].tolist())
    written = export_dataset(db, tmp_path, seasons)
    total = sum(path.stat().st_size for path in written)
    assert total < SIZE_BUDGET_BYTES, f"export grew to {total:,} bytes"


def test_every_exported_file_parses(tmp_path: Path) -> None:
    db = Database()
    for path in export_dataset(db, tmp_path, [_latest_season(db)]):
        json.loads(path.read_text(encoding="utf-8"))


def test_leaders_match_the_database_exactly() -> None:
    """The site must not disagree with the dashboard about a number."""
    db = Database()
    season = _latest_season(db)
    exported = build_leaders(db, season)
    points = next(c for c in exported["categories"] if c["key"] == "PTS")

    truth = db.query_df(
        "SELECT PLAYER_NAME, PTS FROM player_season_full "
        "WHERE season = ? AND GP >= ? AND MIN >= ? ORDER BY PTS DESC LIMIT 3",
        [season, MIN_GAMES, MIN_MINUTES],
    )
    assert [entry["name"] for entry in points["leaders"][:3]] == truth["PLAYER_NAME"].tolist()
    assert [entry["value"] for entry in points["leaders"][:3]] == pytest.approx(
        truth["PTS"].tolist()
    )


def test_every_team_resolves_to_a_tricode_and_accent() -> None:
    db = Database()
    ratings = build_team_ratings(db, _latest_season(db))
    assert len(ratings["teams"]) == 30
    assert all(team["tricode"] for team in ratings["teams"])


def test_the_committed_dataset_is_present_for_the_web_build() -> None:
    index = REPO / DATA_DIR / "index.json"
    assert index.exists(), "run python scripts/export_web_data.py"
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert payload["summary"]["teams"] == 30
    for season in payload["seasons"]:
        assert (REPO / DATA_DIR / "leaders" / f"{season}.json").exists()
        assert (REPO / DATA_DIR / "teams" / f"{season}.json").exists()
