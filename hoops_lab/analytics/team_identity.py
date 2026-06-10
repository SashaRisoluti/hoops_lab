"""Team identity: per-game opponent self-join, season Four Factors, league ranks."""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.four_factors import FACTOR_DIRECTIONS, four_factors
from hoops_lab.features.percentiles import percentile_rank
from hoops_lab.storage.database import Database

_COUNT_COLS = "FGM, FG3M, FGA, FTA, FTM, TOV, OREB, DREB"


def team_game_factors(db: Database, team_id: int, season: str) -> pd.DataFrame:
    """Game-by-game counts for one team with the opponent's counts attached.

    Opponent rows come from the same GAME_ID in ``box_scores_team`` (the
    derivation that also powers the games table). The eight Four Factors
    columns are appended per game.
    """
    own_cols = ", ".join(f"own.{c.strip()}" for c in _COUNT_COLS.split(","))
    opp_cols = ", ".join(f"opp.{c.strip()} AS OPP_{c.strip()}" for c in _COUNT_COLS.split(","))
    games = db.query_df(
        f"""
        SELECT
            own.GAME_ID, own.GAME_DATE, own.season, own.WL, own.PLUS_MINUS,
            {own_cols}, {opp_cols},
            opp.TEAM_ID AS OPP_TEAM_ID,
            opp.TEAM_ABBREVIATION AS OPP_ABBREVIATION
        FROM box_scores_team AS own
        JOIN box_scores_team AS opp
          ON opp.GAME_ID = own.GAME_ID AND opp.TEAM_ID != own.TEAM_ID
        WHERE own.TEAM_ID = ? AND own.season = ?
        ORDER BY own.GAME_DATE
        """,
        [team_id, season],
    )
    return four_factors(games)


def league_team_factors(db: Database, season: str) -> pd.DataFrame:
    """Season Four Factors for every team, with league percentile columns.

    Factors are computed on summed season counts (possession-weighted), not
    averaged per game. Each factor gains a ``<factor>_PCTL`` column where 100
    is always best (lower-is-better factors are ranked on the negated value).
    """
    own_sums = ", ".join(f"sum(own.{c.strip()}) AS {c.strip()}" for c in _COUNT_COLS.split(","))
    opp_sums = ", ".join(f"sum(opp.{c.strip()}) AS OPP_{c.strip()}" for c in _COUNT_COLS.split(","))
    league = db.query_df(
        f"""
        SELECT
            own.TEAM_ID,
            min(own.TEAM_ABBREVIATION) AS TEAM_ABBREVIATION,
            count(*) AS GP,
            sum(own.PLUS_MINUS) AS PLUS_MINUS,
            {own_sums}, {opp_sums}
        FROM box_scores_team AS own
        JOIN box_scores_team AS opp
          ON opp.GAME_ID = own.GAME_ID AND opp.TEAM_ID != own.TEAM_ID
        WHERE own.season = ?
        GROUP BY own.TEAM_ID
        """,
        [season],
    )
    league = four_factors(league)
    for factor, higher_is_better in FACTOR_DIRECTIONS.items():
        series = league[factor] if higher_is_better else -league[factor]
        league[f"{factor}_PCTL"] = percentile_rank(series)
    return league


#: Playmaking & rebounding columns from advanced_team_stats (all higher = better).
PLAYMAKING_REBOUNDING_COLS = ("AST_PCT", "AST_TO", "AST_RATIO", "OREB_PCT", "DREB_PCT", "REB_PCT")


def league_playmaking_rebounding(db: Database, season: str) -> pd.DataFrame:
    """Team playmaking/rebounding profile with league percentile columns."""
    columns = ", ".join(PLAYMAKING_REBOUNDING_COLS)
    league = db.query_df(
        f"SELECT TEAM_ID, {columns} FROM advanced_team_stats WHERE season = ?",
        [season],
    )
    for column in PLAYMAKING_REBOUNDING_COLS:
        league[f"{column}_PCTL"] = percentile_rank(league[column])
    return league


def league_ratings(db: Database, season: str) -> pd.DataFrame:
    """Endpoint-provided team ratings for one season, with league percentiles.

    DEF_RATING is inverted in its percentile (lower is better); PACE gets no
    percentile because faster is not inherently better.
    """
    ratings = db.query_df(
        "SELECT TEAM_ID, TEAM_NAME, W, L, OFF_RATING, DEF_RATING, NET_RATING, PACE "
        "FROM advanced_team_stats WHERE season = ?",
        [season],
    )
    for column, higher_is_better in (
        ("OFF_RATING", True),
        ("DEF_RATING", False),
        ("NET_RATING", True),
    ):
        series = ratings[column] if higher_is_better else -ratings[column]
        ratings[f"{column}_PCTL"] = percentile_rank(series)
    return ratings
