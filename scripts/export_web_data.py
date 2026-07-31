"""Export what the public web app needs from the Python side of the project.

Two independent artifacts, both committed so the site builds with no database:

* ``web/tokens.json`` — the design tokens and readable team accents, generated from
  ``dashboard/components/theme.py``. Maintaining a Tailwind config by hand would let the
  two surfaces drift; a design gate re-runs this export and fails if the artifact is stale.
* ``web/public/data/*.json`` — the real NBA data the pages render, read from DuckDB
  through the same ``hoops_lab.analytics`` functions the dashboard uses. No statistic is
  recomputed here, so the site and the dashboard cannot disagree about a number.

Run from the repo root::

    python scripts/export_web_data.py                 # tokens + dataset
    python scripts/export_web_data.py --tokens-only   # tokens only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Repo root importable regardless of how the script is launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from dashboard.components.theme import TEAM_ACCENTS_READABLE, TOKENS  # noqa: E402
from hoops_lab.analytics.team_identity import league_ratings  # noqa: E402
from hoops_lab.config import DEMO_SEASONS  # noqa: E402
from hoops_lab.storage.database import Database  # noqa: E402

#: Where the generated tokens live, relative to the repo root.
TOKENS_PATH = "web/tokens.json"

#: Where the generated dataset lives, relative to the repo root.
DATA_DIR = "web/public/data"

#: Minimum sample a player must clear to appear in a leaderboard. Mandatory on every
#: analysis surface in this project — a 3-game cameo is not a scoring leader.
MIN_GAMES = 20
MIN_MINUTES = 15.0

#: How many players each leaderboard shows.
TOP_N = 10

#: Attempts a shot zone needs before it is published. Filters out the handful of
#: backcourt heaves, which would otherwise show a wild efficiency on a tiny sample.
MIN_ZONE_ATTEMPTS = 200

#: Leaderboards published per season, as ``(column, label)``.
LEADER_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("PTS", "Points per game"),
    ("AST", "Assists per game"),
    ("REB", "Rebounds per game"),
    ("TS_PCT", "True shooting"),
)

_SOURCE = "dashboard/components/theme.py"


def export_tokens(dest: Path) -> Path:
    """Write the design tokens and readable team accents to ``dest`` as JSON.

    The payload is deterministic on purpose: no timestamp, so re-running the export
    produces a byte-identical file and the drift gate stays meaningful.
    """
    payload = {
        "generatedFrom": _SOURCE,
        "tokens": dict(TOKENS),
        "teamAccents": dict(TEAM_ACCENTS_READABLE),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def _write_json(dest: Path, payload: dict) -> Path:
    """Write ``payload`` to ``dest`` as indented JSON, creating parent directories."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def _rows(db: Database, table: str) -> int:
    """Row count for ``table``, or 0 when it has not been built yet."""
    try:
        return db.table_rows(table)
    except Exception:
        return 0


def build_project_stats(root: Path) -> dict:
    """Counts describing the codebase itself, for the About page.

    Derived from the source tree rather than written down, so the page cannot quote a
    number that stopped being true three commits ago.
    """
    tests = 0
    for path in (root / "tests").rglob("test_*.py"):
        tests += sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("def test_")
        )
    modules = (
        sum(1 for _ in (root / "hoops_lab").rglob("*.py")) if (root / "hoops_lab").exists() else 0
    )
    return {"tests": tests, "modules": modules}


def build_index(db: Database) -> dict:
    """Build the small index every page loads: seasons, teams and headline counts."""
    teams = db.query_df("SELECT team_id, full_name, abbreviation FROM teams ORDER BY abbreviation")
    seasons = sorted(db.query_df("SELECT season FROM seasons")["season"].tolist(), reverse=True)

    return {
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "generatedFrom": "data/db/hoops_lab.duckdb",
        "seasons": seasons,
        "latestSeason": seasons[0] if seasons else None,
        "teams": [
            {
                "id": int(row.team_id),
                "tricode": row.abbreviation,
                "name": row.full_name,
                "accent": TEAM_ACCENTS_READABLE.get(row.abbreviation),
            }
            for row in teams.itertuples()
        ],
        "summary": {
            "seasons": len(seasons),
            "teams": int(len(teams)),
            "games": _rows(db, "games"),
            "players": int(
                db.query_df("SELECT COUNT(DISTINCT PLAYER_ID) n FROM player_season_full")["n"][0]
            )
            if _rows(db, "player_season_full")
            else 0,
            "shots": _rows(db, "shots"),
            "possessions": _rows(db, "possessions"),
        },
        "project": build_project_stats(ROOT),
    }


def build_leaders(
    db: Database,
    season: str,
    top_n: int = TOP_N,
    min_games: int = MIN_GAMES,
    min_minutes: float = MIN_MINUTES,
) -> dict:
    """Build the per-season leaderboards, after applying the minimum-sample filter."""
    players = db.query_df(
        "SELECT PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, GP, MIN, "
        + ", ".join(f'"{column}"' for column, _ in LEADER_CATEGORIES)
        + " FROM player_season_full WHERE season = ? AND GP >= ? AND MIN >= ?",
        [season, min_games, min_minutes],
    )

    categories = []
    for column, label in LEADER_CATEGORIES:
        ranked = players.dropna(subset=[column]).nlargest(top_n, column)
        categories.append(
            {
                "key": column,
                "label": label,
                "leaders": [
                    {
                        "playerId": int(row.PLAYER_ID),
                        "name": row.PLAYER_NAME,
                        "tricode": row.TEAM_ABBREVIATION,
                        "value": float(getattr(row, column)),
                    }
                    for row in ranked.itertuples()
                ],
            }
        )

    return {
        "season": season,
        "minGames": min_games,
        "minMinutes": min_minutes,
        "categories": categories,
    }


def build_team_ratings(db: Database, season: str) -> dict:
    """Build the per-season team ratings, reusing the dashboard's own analytics."""
    ratings = league_ratings(db, season)
    tricodes = db.query_df("SELECT team_id, abbreviation FROM teams")
    lookup = dict(zip(tricodes["team_id"], tricodes["abbreviation"], strict=True))

    def _value(raw: object) -> float | None:
        return None if pd.isna(raw) else float(raw)

    return {
        "season": season,
        "teams": [
            {
                "id": int(row.TEAM_ID),
                "tricode": lookup.get(row.TEAM_ID),
                "name": row.TEAM_NAME,
                "wins": int(row.W),
                "losses": int(row.L),
                "offRating": _value(row.OFF_RATING),
                "defRating": _value(row.DEF_RATING),
                "netRating": _value(row.NET_RATING),
                "pace": _value(row.PACE),
                "offRatingPctl": _value(row.OFF_RATING_PCTL),
                "defRatingPctl": _value(row.DEF_RATING_PCTL),
                "netRatingPctl": _value(row.NET_RATING_PCTL),
            }
            for row in ratings.itertuples()
        ],
    }


def build_shot_zones(db: Database, season: str, min_attempts: int = MIN_ZONE_ATTEMPTS) -> dict:
    """League-wide efficiency per shot zone for one season.

    Points per shot is what makes the zones comparable: a 35% three is worth more than
    a 42% mid-range, and only the points-per-shot column shows it.
    """
    zones = db.query_df(
        "SELECT SHOT_ZONE_BASIC AS zone, "
        "       COUNT(*) AS attempts, "
        "       AVG(SHOT_MADE_FLAG) AS fg_pct, "
        # Value every shot on its own row. Taking the zone's maximum would let the
        # handful of rows the feed mislabels (8 of 22,025 mid-range shots are tagged
        # 3PT) reprice the entire zone.
        "       SUM(SHOT_MADE_FLAG * CASE WHEN SHOT_TYPE LIKE '3PT%' THEN 3 ELSE 2 END) "
        "           / CAST(COUNT(*) AS DOUBLE) AS points_per_shot, "
        "       AVG(CASE WHEN SHOT_TYPE LIKE '3PT%' THEN 1.0 ELSE 0.0 END) AS three_share "
        "FROM shots WHERE season = ? "
        "GROUP BY SHOT_ZONE_BASIC HAVING COUNT(*) >= ? "
        "ORDER BY attempts DESC",
        [season, min_attempts],
    )
    total = int(zones["attempts"].sum()) if not zones.empty else 0

    return {
        "season": season,
        "minAttempts": min_attempts,
        "totalAttempts": total,
        "zones": [
            {
                "zone": row.zone,
                "attempts": int(row.attempts),
                "share": float(row.attempts) / total if total else 0.0,
                "fgPct": float(row.fg_pct),
                "pointsPerShot": float(row.points_per_shot),
                "isThree": float(row.three_share) > 0.5,
            }
            for row in zones.itertuples()
        ],
    }


def export_dataset(db: Database, root: Path, seasons: list[str]) -> list[Path]:
    """Write the index plus per-season leaders and team ratings under ``root``."""
    written = [_write_json(root / "index.json", build_index(db))]
    for season in seasons:
        written.append(_write_json(root / "leaders" / f"{season}.json", build_leaders(db, season)))
        written.append(
            _write_json(root / "teams" / f"{season}.json", build_team_ratings(db, season))
        )
        written.append(
            _write_json(root / "shot-zones" / f"{season}.json", build_shot_zones(db, season))
        )
    return written


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export web app data from the Python project.")
    parser.add_argument(
        "--tokens-only",
        action="store_true",
        help="Write only web/tokens.json (design tokens and team accents).",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        default=DEMO_SEASONS,
        help="Seasons to export (default: DEMO_SEASONS).",
    )
    args = parser.parse_args()

    written = export_tokens(ROOT / TOKENS_PATH)
    print(f"wrote {written.relative_to(ROOT)}")

    if args.tokens_only:
        return 0

    db = Database()
    try:
        paths = export_dataset(db, ROOT / DATA_DIR, list(args.seasons))
    finally:
        db.close()

    total = sum(path.stat().st_size for path in paths)
    for path in paths:
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")
    print(f"{len(paths)} files, {total / 1024:.1f} KB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
