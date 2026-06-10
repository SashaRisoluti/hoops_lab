"""Complete player profile: percentile radar and lineup-based on/off impact.

The radar compares one player-season row against the filtered population
(percentiles, with lower-is-better stats inverted). The on/off impact is
plus/minus-based and derives from the COMPLETE 5-man lineup population
downloaded per team — not from a capped sample.
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.percentiles import percentile_rank
from hoops_lab.storage.database import Database

#: Radar axes: label -> (column in player_season_full, higher_is_better).
#: A "Clutch" axis will join once clutch splits are ingested (Phase 5+).
RADAR_CATEGORIES: dict[str, tuple[str, bool]] = {
    "Scoring": ("PTS", True),
    "Efficiency": ("TS_PCT", True),
    "Playmaking": ("AST_PCT", True),
    "Rebounding": ("REB_PCT", True),
    "Defense": ("DEF_RATING", False),  # lower rating = better defense
    "Usage": ("USG_PCT", True),
}


def radar_percentiles(
    population: pd.DataFrame,
    row_idx: int,
    categories: dict[str, tuple[str, bool]] = RADAR_CATEGORIES,
) -> dict[str, float]:
    """Percentile per radar category for one row of the filtered population.

    Lower-is-better stats are ranked on the negated series, so the best
    value always maps to the 100th percentile. Categories whose column is
    missing from ``population`` are skipped.
    """
    values: dict[str, float] = {}
    for label, (column, higher_is_better) in categories.items():
        if column not in population.columns:
            continue
        series = population[column] if higher_is_better else -population[column]
        values[label] = float(percentile_rank(series).iloc[row_idx])
    return values


def player_on_off(
    db: Database,
    player_id: int,
    team_id: int,
    season: str,
) -> dict[str, float] | None:
    """Plus/minus-based on/off per 48 minutes, from the complete lineups.

    ON  = aggregate plus/minus and clock minutes of the team's 5-man lineups
          featuring the player (GROUP_ID token match).
    OFF = team season totals minus the ON share. Team clock minutes come from
          the team box scores (whose MIN is player-minutes, i.e. clock x 5).

    Returns
    -------
    Dict with on/off minutes, plus/minus and per-48 rates, or None when the
    player has no lineup minutes for that team/season (or the team's bench
    never sat them, leaving no OFF sample).
    """
    on = db.query_df(
        "SELECT coalesce(sum(MIN), 0) AS m, coalesce(sum(PLUS_MINUS), 0) AS pm "
        "FROM lineups WHERE season = ? AND TEAM_ID = ? AND GROUP_ID LIKE ?",
        [season, team_id, f"%-{player_id}-%"],
    ).iloc[0]
    team = db.query_df(
        "SELECT coalesce(sum(MIN), 0) / 5.0 AS m, coalesce(sum(PLUS_MINUS), 0) AS pm "
        "FROM box_scores_team WHERE season = ? AND TEAM_ID = ?",
        [season, team_id],
    ).iloc[0]

    on_min, on_pm = float(on["m"]), float(on["pm"])
    team_min, team_pm = float(team["m"]), float(team["pm"])
    off_min, off_pm = team_min - on_min, team_pm - on_pm

    if on_min <= 0 or off_min <= 0:
        return None

    on_per48 = on_pm / on_min * 48.0
    off_per48 = off_pm / off_min * 48.0
    return {
        "on_min": on_min,
        "off_min": off_min,
        "on_pm": on_pm,
        "off_pm": off_pm,
        "on_pm_per48": on_per48,
        "off_pm_per48": off_per48,
        "on_off_per48": on_per48 - off_per48,
    }
