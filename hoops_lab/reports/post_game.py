"""Automated post-game report: factors, runs, shot quality, WP swing, insights.

Assembles every Phase 4-6 building block for one ingested game. Shot-quality
sections appear only for teams with shot-location data (the reference team,
per the demo data strategy).
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.four_factors import four_factors
from hoops_lab.models.run_detector import detect_runs
from hoops_lab.models.shot_quality_model import score_shots
from hoops_lab.storage.database import Database

_COUNTS = "FGM, FG3M, FGA, FTA, FTM, TOV, OREB, DREB"


def game_header(db: Database, game_id: str) -> dict:
    """Teams, date, season and final score for one game."""
    row = db.query_df(
        """
        SELECT g.game_id, g.season, g.game_date, g.home_pts, g.away_pts,
               th.abbreviation AS home_abbr, ta.abbreviation AS away_abbr,
               g.home_team_id, g.away_team_id
        FROM games AS g
        JOIN teams AS th ON th.team_id = g.home_team_id
        JOIN teams AS ta ON ta.team_id = g.away_team_id
        WHERE g.game_id = ?
        """,
        [game_id],
    ).iloc[0]
    return row.to_dict()


def game_four_factors(db: Database, game_id: str) -> pd.DataFrame:
    """Both teams' Four Factors for one game (opponent self-join)."""
    own = ", ".join(f"own.{c.strip()}" for c in _COUNTS.split(","))
    opp = ", ".join(f"opp.{c.strip()} AS OPP_{c.strip()}" for c in _COUNTS.split(","))
    counts = db.query_df(
        f"""
        SELECT own.TEAM_ID, own.TEAM_ABBREVIATION, own.PTS, {own}, {opp}
        FROM box_scores_team AS own
        JOIN box_scores_team AS opp
          ON opp.GAME_ID = own.GAME_ID AND opp.TEAM_ID != own.TEAM_ID
        WHERE own.GAME_ID = ?
        """,
        [game_id],
    )
    return four_factors(counts)


def shot_quality_summary(db: Database, game_id: str, shot_model) -> dict | None:
    """Actual vs expected points for the game's tracked shots (if any)."""
    shots = db.query_df("SELECT * FROM shots WHERE GAME_ID = ?", [game_id])
    if shots.empty or shot_model is None:
        return None
    scored = score_shots(shot_model, shots)
    is_three = scored["SHOT_TYPE"].astype(str).str.contains("3PT")
    scored["ACTUAL_PTS"] = scored["SHOT_MADE_FLAG"] * is_three.map({True: 3, False: 2})
    by_player = (
        scored.groupby("PLAYER_NAME")
        .agg(
            attempts=("SHOT_MADE_FLAG", "size"),
            actual=("ACTUAL_PTS", "sum"),
            expected=("XPTS", "sum"),
        )
        .reset_index()
    )
    by_player["above_expected"] = by_player["actual"] - by_player["expected"]
    return {
        "team_abbr": str(scored["TEAM_NAME"].iloc[0]) if "TEAM_NAME" in scored else "",
        "attempts": int(len(scored)),
        "actual_pts": float(scored["ACTUAL_PTS"].sum()),
        "expected_pts": float(scored["XPTS"].sum()),
        "by_player": by_player.sort_values("above_expected", ascending=False),
    }


def top_players(db: Database, game_id: str, n: int = 6) -> pd.DataFrame:
    """Best individual lines of the game."""
    return db.query_df(
        """
        SELECT PLAYER_NAME, TEAM_ABBREVIATION, MIN, PTS, REB, AST, PLUS_MINUS
        FROM box_scores_player
        WHERE GAME_ID = ?
        ORDER BY PTS DESC
        LIMIT ?
        """,
        [game_id, n],
    )


def game_runs(db: Database, game_id: str) -> pd.DataFrame:
    """Detected scoring runs from the game's segmented possessions."""
    possessions = db.query_df("SELECT * FROM possessions WHERE game_id = ?", [game_id])
    if possessions.empty:
        return pd.DataFrame()
    return detect_runs(possessions)


def generate_insights(
    header: dict,
    factors: pd.DataFrame,
    runs: pd.DataFrame,
    shots: dict | None,
    teams_by_id: dict[int, str],
) -> list[str]:
    """3-5 readable bullets distilled from the report sections."""
    insights: list[str] = []

    margin = int(header["home_pts"] - header["away_pts"])
    winner = header["home_abbr"] if margin > 0 else header["away_abbr"]
    insights.append(
        f"**{winner}** won {max(header['home_pts'], header['away_pts'])}-"
        f"{min(header['home_pts'], header['away_pts'])} ({abs(margin):+d})."
    )

    if len(factors) == 2:
        a, b = factors.iloc[0], factors.iloc[1]
        efg_gap = float(a["OFF_EFG"] - b["OFF_EFG"])
        leader = a if efg_gap > 0 else b
        trailer = b if efg_gap > 0 else a
        insights.append(
            f"Shooting battle: **{leader['TEAM_ABBREVIATION']}** {leader['OFF_EFG']:.1%} eFG "
            f"vs {trailer['OFF_EFG']:.1%}."
        )

    if not runs.empty:
        biggest = (
            runs.assign(swing=runs["points_for"] - runs["points_against"])
            .nlargest(1, "swing")
            .iloc[0]
        )
        team = teams_by_id.get(int(biggest["team_id"]), str(biggest["team_id"]))
        insights.append(
            f"Biggest run: **{team}** {biggest['points_for']}-{biggest['points_against']} "
            f"(possessions {biggest['start_possession']}-{biggest['end_possession']})."
        )

    if shots is not None:
        gap = shots["actual_pts"] - shots["expected_pts"]
        verb = "over-performed" if gap >= 0 else "under-performed"
        insights.append(
            f"Shot quality: {shots['actual_pts']:.0f} actual vs {shots['expected_pts']:.1f} "
            f"expected points ({gap:+.1f} — {verb} the looks generated)."
        )

    return insights
