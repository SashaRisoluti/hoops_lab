"""Load raw Parquet files into the analytical DuckDB database.

Parquet-backed tables keep every source column and gain a ``season`` column
extracted from the file name; ``teams`` / ``players`` / ``seasons`` / ``games``
are derived afterwards. Missing raw datasets are skipped with a warning so a
partial download still produces a usable database.

Run as a module to (re)build the database from ``data/raw``::

    python -m hoops_lab.storage.seed
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from nba_api.stats.static import teams as static_teams

from hoops_lab.features.possession import build_possessions
from hoops_lab.ingestion.nba_api_client import RAW_DATA_DIR
from hoops_lab.storage.database import Database
from hoops_lab.storage.models import PARQUET_TABLES

logger = logging.getLogger(__name__)

#: Versioned demo parquet (used when data/raw is empty, e.g. on HF Spaces).
PROCESSED_DATA_DIR = Path("data/processed")

#: Advanced columns exposed by the player_season_full view (when present in
#: the ingested data and not already part of the base table).
ADVANCED_VIEW_COLUMNS: tuple[str, ...] = (
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "AST_PCT",
    "AST_TO",
    "AST_RATIO",
    "OREB_PCT",
    "DREB_PCT",
    "REB_PCT",
    "TM_TOV_PCT",
    "EFG_PCT",
    "TS_PCT",
    "USG_PCT",
    "PACE",
    "PIE",
    "POSS",
)


def _column_names(db: Database, table: str) -> set[str]:
    """Column names of a table, from the information schema."""
    rows = db.query_df(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
    )
    return set(rows["column_name"])


def _sql_glob(raw_dir: Path, pattern: str) -> str:
    """Build a single-quote-safe, forward-slash glob for read_parquet()."""
    return str(raw_dir / pattern).replace("\\", "/").replace("'", "''")


def load_parquet_tables(db: Database, raw_dir: Path) -> dict[str, int]:
    """Create one table per raw dataset found in ``raw_dir``.

    Returns
    -------
    Mapping of table name to loaded row count (skipped datasets excluded).
    """
    counts: dict[str, int] = {}
    for table, pattern in PARQUET_TABLES.items():
        if not sorted(raw_dir.glob(pattern)):
            logger.warning("No files match %s — skipping table %s", pattern, table)
            continue
        sql = (
            f'CREATE OR REPLACE TABLE "{table}" AS '
            "SELECT * EXCLUDE (filename), "
            "regexp_extract(filename, '(\\d{4}-\\d{2})\\.parquet$', 1) AS season "
            f"FROM read_parquet('{_sql_glob(raw_dir, pattern)}', filename=true)"
        )
        db.execute(sql)
        counts[table] = db.table_rows(table)
        logger.info("Loaded %s: %d rows", table, counts[table])
    return counts


def derive_core_tables(db: Database) -> dict[str, int]:
    """Build teams, games, players and seasons from loaded data.

    Each derivation is skipped (with a warning) when its source table is
    missing, so partial raw data still yields a usable database.
    """
    counts: dict[str, int] = {}

    teams_df = pd.DataFrame(static_teams.get_teams())  # offline static data
    db.connect().register("teams_src", teams_df)
    db.execute(
        "CREATE OR REPLACE TABLE teams AS "
        "SELECT id AS team_id, full_name, abbreviation, nickname, city, state, year_founded "
        "FROM teams_src"
    )
    counts["teams"] = db.table_rows("teams")

    if db.has_table("box_scores_team"):
        # Neutral-site games (NBA Cup knockout, Mexico City, Paris, ...) have
        # BOTH team rows in "@" format. Keep them: the row with the "vs."
        # pattern is the home side when present, otherwise the lower TEAM_ID
        # becomes the nominal home and the game is flagged neutral_site.
        db.execute(
            """
            CREATE OR REPLACE TABLE games AS
            WITH ranked AS (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY GAME_ID
                        ORDER BY (CASE WHEN MATCHUP LIKE '% vs. %' THEN 0 ELSE 1 END), TEAM_ID
                    ) AS rn,
                    sum(CASE WHEN MATCHUP LIKE '% vs. %' THEN 1 ELSE 0 END)
                        OVER (PARTITION BY GAME_ID) AS home_pattern_rows
                FROM box_scores_team
            )
            SELECT
                h.GAME_ID AS game_id,
                h.season AS season,
                CASE substr(CAST(h.SEASON_ID AS VARCHAR), 1, 1)
                    WHEN '2' THEN 'Regular Season'
                    WHEN '4' THEN 'Playoffs'
                    WHEN '1' THEN 'Pre Season'
                    ELSE 'Other'
                END AS season_type,
                CAST(h.GAME_DATE AS DATE) AS game_date,
                h.TEAM_ID AS home_team_id,
                a.TEAM_ID AS away_team_id,
                h.PTS AS home_pts,
                a.PTS AS away_pts,
                (h.home_pattern_rows = 0) AS neutral_site
            FROM ranked AS h
            JOIN ranked AS a ON h.GAME_ID = a.GAME_ID AND a.rn = 2
            WHERE h.rn = 1
            """
        )
        counts["games"] = db.table_rows("games")

        db.execute(
            "CREATE OR REPLACE TABLE seasons AS "
            "SELECT season, season_type, count(*) AS games, "
            "min(game_date) AS first_game, max(game_date) AS last_game "
            "FROM games GROUP BY season, season_type ORDER BY season"
        )
        counts["seasons"] = db.table_rows("seasons")
    else:
        logger.warning("box_scores_team missing — games/seasons not derived")

    if db.has_table("player_season_stats"):
        db.execute(
            """
            CREATE OR REPLACE TABLE players AS
            SELECT
                PLAYER_ID AS player_id,
                PLAYER_NAME AS full_name,
                TEAM_ID AS team_id,
                TEAM_ABBREVIATION AS team_abbreviation,
                AGE AS age,
                season AS last_season
            FROM (
                SELECT *, row_number() OVER (PARTITION BY PLAYER_ID ORDER BY season DESC) AS rn
                FROM player_season_stats
            )
            WHERE rn = 1
            """
        )
        counts["players"] = db.table_rows("players")
    else:
        logger.warning("player_season_stats missing — players not derived")

    if db.has_table("player_season_stats") and db.has_table("advanced_player_stats"):
        base_cols = _column_names(db, "player_season_stats")
        advanced_cols = _column_names(db, "advanced_player_stats")
        extras = [c for c in ADVANCED_VIEW_COLUMNS if c in advanced_cols and c not in base_cols]
        extra_select = "".join(f', a."{c}"' for c in extras)
        db.execute(
            "CREATE OR REPLACE VIEW player_season_full AS "
            f"SELECT b.*{extra_select} FROM player_season_stats AS b "
            "LEFT JOIN advanced_player_stats AS a "
            "ON a.PLAYER_ID = b.PLAYER_ID AND a.season = b.season"
        )
        counts["player_season_full"] = db.table_rows("player_season_full")
    else:
        logger.warning("base/advanced player stats missing — player_season_full view not created")

    return counts


def seed_database(
    db: Database,
    raw_dir: str | Path | None = None,
    fallback_dir: str | Path | None = None,
) -> dict[str, int]:
    """Full seed: Parquet-backed tables, derived tables, then possessions.

    Parameters
    ----------
    db:
        Target database (migrations are expected to have run already).
    raw_dir:
        Directory with the raw Parquet files (default: ``RAW_DATA_DIR``).
    fallback_dir:
        Used when ``raw_dir`` holds no parquet at all — on HF Spaces the raw
        downloads are gitignored and the versioned demo parquet live in
        ``data/processed`` (default).

    Returns
    -------
    Mapping of table name to row count for everything that was (re)built.
    """
    raw_path = Path(raw_dir) if raw_dir is not None else RAW_DATA_DIR
    fallback_path = Path(fallback_dir) if fallback_dir is not None else PROCESSED_DATA_DIR
    if not any(raw_path.glob("*.parquet")) and any(fallback_path.glob("*.parquet")):
        logger.info("No parquet in %s — falling back to %s", raw_path, fallback_path)
        raw_path = fallback_path

    counts = load_parquet_tables(db, raw_path)
    counts.update(derive_core_tables(db))

    if db.has_table("play_by_play") and db.table_rows("play_by_play") > 0:
        possessions = build_possessions(db.query_df("SELECT * FROM play_by_play"))
        db.connect().register("possessions_src", possessions)
        db.execute("CREATE OR REPLACE TABLE possessions AS SELECT * FROM possessions_src")
        counts["possessions"] = db.table_rows("possessions")

    logger.info("Seed complete: %d tables", len(counts))
    return counts


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    database = Database()
    database.run_migrations()
    table_counts = seed_database(database)

    width = max(len(name) for name in table_counts)
    for name, rows in table_counts.items():
        print(f"{name:<{width}}  {rows:>9,}")
    print(f"Database ready at {database.path}")
