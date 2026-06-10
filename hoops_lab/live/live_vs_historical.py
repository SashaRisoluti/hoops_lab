"""Live vs historical comparison: season baselines and delta tables."""

from __future__ import annotations

import pandas as pd

from hoops_lab.live.game_state import GameState
from hoops_lab.storage.database import Database


def get_baselines(db: Database, team_id: int, season: str) -> dict[str, float]:
    """Season baselines (eFG%, TOV%, pace, off. rating) for one team."""
    rows = db.query_df(
        "SELECT EFG_PCT, TM_TOV_PCT, PACE, OFF_RATING FROM advanced_team_stats "
        "WHERE TEAM_ID = ? AND season = ?",
        [team_id, season],
    )
    if rows.empty:
        return {}
    return {k: float(v) for k, v in rows.iloc[0].items()}


def comparison_table(
    state: GameState,
    team_id: int,
    baseline: dict[str, float],
) -> pd.DataFrame:
    """Live vs season metrics for one team, with deltas."""
    stats = state.team_stats[team_id]
    ppp = state.ppp(team_id)
    rows = [
        {
            "metric": "eFG%",
            "live": stats.efg_pct,
            "season": baseline.get("EFG_PCT"),
        },
        {
            "metric": "Off. rating (PPP x 100)",
            "live": ppp * 100.0 if ppp is not None else None,
            "season": baseline.get("OFF_RATING"),
        },
        {
            "metric": "Pace",
            "live": state.pace_estimate,
            "season": baseline.get("PACE"),
        },
    ]
    table = pd.DataFrame(rows)
    table["delta"] = table["live"] - table["season"]
    return table
