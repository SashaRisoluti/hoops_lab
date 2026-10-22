"""Which season the project features by default."""

from __future__ import annotations

from hoops_lab.config import FEATURED_MIN_TEAM_GAMES
from hoops_lab.storage.database import Database


def featured_season(db: Database, min_team_games: int = FEATURED_MIN_TEAM_GAMES) -> str | None:
    """Newest season in which every team has played at least ``min_team_games`` games.

    A season that has only just started stays selectable everywhere, but the
    default falls back to the previous season until its sample is meaningful.

    Args:
        db: Database with the derived ``games`` table.
        min_team_games: Games each team must have played for a season to qualify.

    Returns:
        The featured season label; the newest season when none qualifies yet;
        ``None`` when there are no games at all.
    """
    if not db.has_table("games"):  # fresh database, nothing seeded yet
        return None
    per_season = db.query_df(
        """
        WITH team_games AS (
            SELECT season, home_team_id AS team_id FROM games
            UNION ALL
            SELECT season, away_team_id AS team_id FROM games
        ), per_team AS (
            SELECT season, team_id, count(*) AS games FROM team_games GROUP BY season, team_id
        )
        SELECT season, min(games) AS min_games FROM per_team
        GROUP BY season ORDER BY season DESC
        """
    )
    if per_season.empty:
        return None
    qualified = per_season.loc[per_season["min_games"] >= min_team_games, "season"]
    return str(qualified.iloc[0] if len(qualified) else per_season["season"].iloc[0])
