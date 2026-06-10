"""Lineup recommendation by shrunken plus/minus.

MVP version: empirical-Bayes style shrinkage of +/- per 48 toward zero,
``PM / (MIN + prior_minutes) * 48`` — proven minutes beat small-sample
spikes. Matchup- and fatigue-aware recommendations need opponent-specific
lineup data and rotation tracking (future work, declared).
"""

from __future__ import annotations

import pandas as pd


def recommend_lineups(
    lineups: pd.DataFrame,
    top_n: int = 5,
    prior_minutes: float = 96.0,
) -> pd.DataFrame:
    """Rank lineups by shrunken +/- per 48 minutes.

    Parameters
    ----------
    lineups:
        Frame with at least MIN and PLUS_MINUS columns.
    top_n:
        How many lineups to return.
    prior_minutes:
        Shrinkage strength: pseudo-minutes of league-average (zero) play.
    """
    out = lineups.copy()
    out["PM_PER48_SHRUNK"] = out["PLUS_MINUS"] / (out["MIN"] + prior_minutes) * 48.0
    return out.sort_values("PM_PER48_SHRUNK", ascending=False).head(top_n).reset_index(drop=True)
