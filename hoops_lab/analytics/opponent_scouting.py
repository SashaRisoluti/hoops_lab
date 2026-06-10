"""Automated opponent scouting: strengths/weaknesses, key players, top lineups.

Tendencies are stats-based (Four Factors percentiles, usage hierarchy,
lineup plus/minus). Play-type frequencies (isolation, pick-and-roll, ...)
require Synergy-style data not yet ingested — planned with the possession
work in Phase 4+.
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.four_factors import FACTOR_LABELS
from hoops_lab.storage.database import Database


def strengths_weaknesses(
    league: pd.DataFrame,
    team_id: int,
    top_k: int = 3,
) -> tuple[list[str], list[str]]:
    """Readable bullets for a team's best and worst Four Factors percentiles.

    Parameters
    ----------
    league:
        Output of ``team_identity.league_team_factors`` (factors + _PCTL).
    team_id:
        Team to profile.
    top_k:
        How many bullets per list.
    """
    row = league.loc[league["TEAM_ID"] == team_id].iloc[0]
    ranked = sorted(
        FACTOR_LABELS,
        key=lambda factor: float(row[f"{factor}_PCTL"]),
        reverse=True,
    )

    def bullet(factor: str) -> str:
        value = row[factor]
        formatted = f"{value:.1%}" if "EFG" in factor or "RATE" in factor else f"{value:.1f}%"
        return f"{FACTOR_LABELS[factor]}: {formatted} — {row[f'{factor}_PCTL']:.0f}th pctl"

    strengths = [bullet(f) for f in ranked[:top_k]]
    weaknesses = [bullet(f) for f in ranked[-top_k:][::-1]]
    return strengths, weaknesses


def top_players(db: Database, team_id: int, season: str, n: int = 6) -> pd.DataFrame:
    """The opponent's offensive hierarchy: who creates and who finishes."""
    return db.query_df(
        """
        SELECT PLAYER_NAME, GP, MIN, PTS, AST, REB, USG_PCT, TS_PCT, NET_RATING
        FROM player_season_full
        WHERE TEAM_ID = ? AND season = ? AND MIN >= 15
        ORDER BY USG_PCT DESC
        LIMIT ?
        """,
        [team_id, season, n],
    )


def top_lineups(
    db: Database,
    team_id: int,
    season: str,
    min_minutes: float = 50,
    n: int = 5,
) -> pd.DataFrame:
    """The opponent's most effective 5-man lineups (plus/minus per 48')."""
    return db.query_df(
        """
        SELECT GROUP_NAME AS lineup, MIN AS minutes, PLUS_MINUS,
               PLUS_MINUS / MIN * 48.0 AS pm_per48
        FROM lineups
        WHERE TEAM_ID = ? AND season = ? AND MIN >= ?
        ORDER BY pm_per48 DESC
        LIMIT ?
        """,
        [team_id, season, min_minutes, n],
    )
