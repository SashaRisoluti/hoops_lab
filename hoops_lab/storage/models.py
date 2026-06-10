"""Table registry for the analytical database.

Three groups of tables, with a single source of truth each:

* **Parquet-backed** — created by the seeder straight from the raw Parquet
  files (schema inferred, every source column preserved, plus a ``season``
  column extracted from the file name). Registry: :data:`PARQUET_TABLES`.
* **Derived** — built by the seeder from the Parquet-backed tables or from
  nba_api static data: ``teams``, ``players``, ``seasons``, ``games``.
* **Structural** — empty tables created by the SQL migrations in
  ``storage/migrations/`` (possessions, percentile cache, live events,
  alerts); they are filled by later phases.
"""

from __future__ import annotations

#: table name -> raw file glob (relative to the raw data directory).
PARQUET_TABLES: dict[str, str] = {
    "box_scores_player": "player_box_*.parquet",
    "box_scores_team": "team_box_*.parquet",
    "player_season_stats": "player_stats_*.parquet",
    "advanced_player_stats": "player_advanced_*.parquet",
    "team_season_stats": "team_stats_*.parquet",
    "advanced_team_stats": "team_advanced_*.parquet",
    "lineups": "lineups_*.parquet",
    "shots": "shot_chart_*.parquet",
    "play_by_play": "play_by_play_sample_*.parquet",
}

#: Tables derived by the seeder from other tables / static data.
DERIVED_TABLES: tuple[str, ...] = ("teams", "players", "seasons", "games")

#: Empty tables owned by the SQL migrations, filled in later phases.
STRUCTURAL_TABLES: tuple[str, ...] = (
    "possessions",
    "player_percentiles",
    "live_game_events",
    "alerts",
)

#: Everything the database is expected to contain once seeded.
EXPECTED_TABLES: tuple[str, ...] = tuple(PARQUET_TABLES) + DERIVED_TABLES + STRUCTURAL_TABLES
