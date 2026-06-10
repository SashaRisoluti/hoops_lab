"""Unit tests for team identity analytics (opponent self-join, league factors)."""

from __future__ import annotations

import pandas as pd

from hoops_lab.analytics.team_identity import league_team_factors, team_game_factors
from hoops_lab.storage.database import Database


def _db() -> Database:
    db = Database(path=":memory:")
    con = db.connect()

    # Two teams, two games. Team 1 posts the stronger shooting numbers.
    t1 = {
        "FGM": 40.0,
        "FG3M": 10.0,
        "FGA": 80.0,
        "FTA": 20.0,
        "FTM": 16.0,
        "TOV": 12.0,
        "OREB": 10.0,
        "DREB": 30.0,
    }
    t2 = {
        "FGM": 35.0,
        "FG3M": 8.0,
        "FGA": 85.0,
        "FTA": 25.0,
        "FTM": 20.0,
        "TOV": 15.0,
        "OREB": 12.0,
        "DREB": 33.0,
    }
    rows = []
    for game_id, date in (("g1", "2024-01-01"), ("g2", "2024-01-05")):
        rows.append(
            {
                "GAME_ID": game_id,
                "GAME_DATE": date,
                "season": "2023-24",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "AAA",
                "WL": "W",
                "PLUS_MINUS": 5.0,
                **t1,
            }
        )
        rows.append(
            {
                "GAME_ID": game_id,
                "GAME_DATE": date,
                "season": "2023-24",
                "TEAM_ID": 2,
                "TEAM_ABBREVIATION": "BBB",
                "WL": "L",
                "PLUS_MINUS": -5.0,
                **t2,
            }
        )
    con.register("box_scores_team", pd.DataFrame(rows))
    return db


def test_team_game_factors_joins_opponent_counts() -> None:
    games = team_game_factors(_db(), team_id=1, season="2023-24")

    assert len(games) == 2
    first = games.iloc[0]
    assert first["OPP_TEAM_ID"] == 2
    assert first["OPP_FGA"] == 85.0  # team 2's attempts in the same game
    assert first["OFF_EFG"] == 0.5625
    assert first["DEF_EFG"] == round(39 / 85, 6) or abs(first["DEF_EFG"] - 39 / 85) < 1e-9


def test_league_team_factors_rank_teams() -> None:
    league = league_team_factors(_db(), season="2023-24")

    assert len(league) == 2
    team1 = league.loc[league["TEAM_ID"] == 1].iloc[0]
    team2 = league.loc[league["TEAM_ID"] == 2].iloc[0]
    # Team 1 shoots better -> top percentile; with 2 teams the scale is [50, 100].
    assert team1["OFF_EFG_PCTL"] == 100.0
    assert team2["OFF_EFG_PCTL"] == 50.0
    # Team 1 also defends the eFG better (DEF_EFG lower) -> inverted percentile.
    assert team1["DEF_EFG_PCTL"] == 100.0
