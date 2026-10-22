"""Unit tests for the storage layer — fully offline, on tmp DuckDB files.

Small Parquet fixtures emulate the raw files produced by the ingestion layer;
the seeder must build the analytical database from them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hoops_lab.storage.database import Database


def _write_fixture_parquets(raw_dir: Path) -> None:
    """Write minimal raw files mimicking the ingestion layer's output."""
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Game 1 is a regular home/away game; game 2 is neutral-site (NBA Cup /
    # Mexico City / Paris style): BOTH rows use the "@" matchup format.
    team_box = pd.DataFrame(
        {
            "SEASON_ID": [22023, 22023, 22023, 22023],
            "TEAM_ID": [1, 2, 4, 3],
            "TEAM_ABBREVIATION": ["AAA", "BBB", "DDD", "CCC"],
            "GAME_ID": ["0022300001", "0022300001", "0022300002", "0022300002"],
            "GAME_DATE": ["2024-01-15", "2024-01-15", "2024-01-20", "2024-01-20"],
            "MATCHUP": ["AAA vs. BBB", "BBB @ AAA", "DDD @ CCC", "CCC @ DDD"],
            "WL": ["W", "L", "W", "L"],
            "PTS": [110, 100, 95, 90],
        }
    )
    team_box.to_parquet(raw_dir / "team_box_2023-24.parquet", index=False)

    player_box = pd.DataFrame(
        {
            "SEASON_ID": [22023],
            "PLAYER_ID": [10],
            "PLAYER_NAME": ["Test Player"],
            "TEAM_ID": [1],
            "GAME_ID": ["0022300001"],
            "PTS": [30],
        }
    )
    player_box.to_parquet(raw_dir / "player_box_2023-24.parquet", index=False)

    # Same player across two seasons: the players table must keep the latest row.
    for season, team_id, age in (("2023-24", 1, 25.0), ("2024-25", 2, 26.0)):
        player_stats = pd.DataFrame(
            {
                "PLAYER_ID": [10],
                "PLAYER_NAME": ["Test Player"],
                "TEAM_ID": [team_id],
                "TEAM_ABBREVIATION": ["AAA" if team_id == 1 else "BBB"],
                "AGE": [age],
                "GP": [70],
                "PTS": [25.0],
            }
        )
        player_stats.to_parquet(raw_dir / f"player_stats_{season}.parquet", index=False)

    # Advanced stats only for 2023-24 (the view must LEFT-join gracefully).
    player_advanced = pd.DataFrame({"PLAYER_ID": [10], "TS_PCT": [0.6], "USG_PCT": [0.31]})
    player_advanced.to_parquet(raw_dir / "player_advanced_2023-24.parquet", index=False)

    # Minimal play-by-play (one made shot) — the seeder must build possessions.
    pbp = pd.DataFrame(
        {
            "gameId": ["0022300001"] * 3,
            "actionNumber": [1, 2, 3],
            "period": [1, 1, 1],
            "clock": ["PT12M00.00S", "PT06M00.00S", "PT00M00.00S"],
            "teamId": [0, 1, 0],
            "location": ["", "h", ""],
            "actionType": ["period", "Made Shot", "period"],
            "subType": ["start", "Jump Shot", "end"],
            "description": ["", "Shot", ""],
            "scoreHome": ["", "2", ""],
            "scoreAway": ["", "0", ""],
        }
    )
    pbp.to_parquet(raw_dir / "play_by_play_sample_2023-24.parquet", index=False)


def _make_db(tmp_path: Path) -> tuple[Database, Path]:
    raw_dir = tmp_path / "raw"
    _write_fixture_parquets(raw_dir)
    db = Database(path=tmp_path / "db" / "test.duckdb")
    return db, raw_dir


def test_ensure_db_ready_builds_database_from_parquet(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)

    seeded = db.ensure_db_ready(raw_dir=raw_dir)

    assert seeded is True
    assert db.table_rows("box_scores_team") == 4
    assert db.table_rows("box_scores_player") == 1
    # Second call: database is already populated, no reseed.
    assert db.ensure_db_ready(raw_dir=raw_dir) is False


def test_games_derived_with_home_away_and_season(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    games = db.query_df("SELECT * FROM games ORDER BY game_id")

    assert len(games) == 2  # no game may be dropped
    game = games.iloc[0]
    assert game["home_team_id"] == 1
    assert game["away_team_id"] == 2
    assert game["home_pts"] == 110
    assert game["away_pts"] == 100
    assert game["season"] == "2023-24"
    assert game["season_type"] == "Regular Season"
    assert not game["neutral_site"]


def test_neutral_site_games_kept_and_flagged(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    game = db.query_df("SELECT * FROM games WHERE game_id = '0022300002'").iloc[0]

    # Both source rows say "@": keep the game, flag it, pick the lower
    # TEAM_ID as the nominal home side (deterministic, documented choice).
    assert game["neutral_site"]
    assert game["home_team_id"] == 3
    assert game["away_team_id"] == 4
    assert game["home_pts"] == 90
    assert game["away_pts"] == 95


def test_players_keep_latest_season_row(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    players = db.query_df("SELECT * FROM players WHERE player_id = 10")

    assert len(players) == 1
    assert players.iloc[0]["team_id"] == 2  # from 2024-25, the latest season
    assert players.iloc[0]["last_season"] == "2024-25"


def test_teams_loaded_from_static_data(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    assert db.table_rows("teams") == 30
    dallas = db.query_df("SELECT full_name FROM teams WHERE team_id = 1610612742")
    assert dallas.iloc[0]["full_name"] == "Dallas Mavericks"


def test_missing_parquet_datasets_are_skipped(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    # No lineups/shots/play-by-play fixtures on disk: tables simply absent.
    assert not db.has_table("lineups")
    assert not db.has_table("shots")


def test_player_season_full_view_joins_advanced(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    row = db.query_df(
        "SELECT PLAYER_NAME, PTS, TS_PCT FROM player_season_full "
        "WHERE PLAYER_ID = 10 AND season = '2023-24'"
    ).iloc[0]

    assert row["PTS"] == 25.0  # from the base table
    assert row["TS_PCT"] == 0.6  # joined from advanced stats


def test_seed_builds_possessions_from_play_by_play(tmp_path) -> None:
    db, raw_dir = _make_db(tmp_path)
    db.ensure_db_ready(raw_dir=raw_dir)

    # The fixture game has exactly one possession (a made shot worth 2).
    assert db.table_rows("possessions") == 1
    possession = db.query_df("SELECT * FROM possessions").iloc[0]
    assert possession["points"] == 2
    assert possession["ended_by"] == "made_fg"


def test_seed_falls_back_to_processed_dir_when_raw_is_empty(tmp_path) -> None:
    # Hosted-demo scenario: data/raw is gitignored (empty), the versioned demo
    # parquet live in the processed directory instead.
    processed = tmp_path / "processed"
    _write_fixture_parquets(processed)
    empty_raw = tmp_path / "raw"
    empty_raw.mkdir()

    db = Database(path=tmp_path / "db" / "test.duckdb")
    seeded = db.ensure_db_ready(raw_dir=empty_raw, fallback_dir=processed)

    assert seeded is True
    assert db.table_rows("games") == 2
    assert db.table_rows("possessions") == 1


def test_migrations_create_structural_tables_and_are_idempotent(tmp_path) -> None:
    db = Database(path=tmp_path / "db" / "test.duckdb")

    first = db.run_migrations()
    second = db.run_migrations()

    assert first  # at least the initial migration applied
    assert second == []  # nothing to re-apply
    for table in ("possessions", "player_percentiles", "live_game_events", "alerts"):
        assert db.has_table(table)


def test_an_unreadable_database_file_is_rebuilt_not_fatal(tmp_path) -> None:
    """The DB is a cache of the parquet: a file from another DuckDB version is replaced.

    Streamlit Cloud once booted on DuckDB 2.0, which left a file DuckDB 1.5 cannot read
    ("created with a newer version of DuckDB"); the app must rebuild, not crash.
    """
    raw_dir = tmp_path / "raw"
    _write_fixture_parquets(raw_dir)
    db_path = tmp_path / "db" / "stale.duckdb"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"written by some other DuckDB" * 200)

    db = Database(path=db_path)

    assert db.ensure_db_ready(raw_dir=raw_dir) is True
    assert db.table_rows("box_scores_team") == 4


def test_ensure_db_ready_reseeds_when_the_parquet_change(tmp_path) -> None:
    """Streamlit Cloud updates the repo in place after a data push, without restarting.

    The database must notice the new parquet and rebuild, or the weekly refresh would
    never reach the hosted dashboard.
    """
    db, raw_dir = _make_db(tmp_path)
    assert db.ensure_db_ready(raw_dir=raw_dir) is True

    team_box = pd.read_parquet(raw_dir / "team_box_2023-24.parquet")
    team_box["GAME_ID"] = team_box["GAME_ID"].str.replace("00223", "00224")
    team_box.to_parquet(raw_dir / "team_box_2024-25.parquet", index=False)

    assert db.ensure_db_ready(raw_dir=raw_dir) is True
    assert "2024-25" in db.query_df("SELECT season FROM seasons")["season"].tolist()
    assert db.ensure_db_ready(raw_dir=raw_dir) is False  # stable once rebuilt
