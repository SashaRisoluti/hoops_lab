"""Analytics for the Overview dashboard: flags, shot zones, standings.

Pure, data-grounded counterparts of the design's mock content: tactical
flags compare the last five games with the season baseline; shot zones map
ShotChartDetail's basic zones to the four design buckets; the conference
standing ranks real wins.
"""

from __future__ import annotations

import pandas as pd

#: ShotChartDetail SHOT_ZONE_BASIC -> design zone bucket (None = excluded).
_ZONE_BUCKETS: dict[str, str | None] = {
    "Restricted Area": "RIM",
    "In The Paint (Non-RA)": "MID",
    "Mid-Range": "MID",
    "Left Corner 3": "CORNER 3",
    "Right Corner 3": "CORNER 3",
    "Above the Break 3": "ABOVE BREAK 3",
    "Backcourt": None,
}

#: Conference membership by tricode (kept in sync with the rail design).
_WEST = {
    "DAL",
    "DEN",
    "GSW",
    "HOU",
    "LAC",
    "LAL",
    "MEM",
    "MIN",
    "NOP",
    "OKC",
    "PHX",
    "POR",
    "SAC",
    "SAS",
    "UTA",
}

#: Flag thresholds (last-5 vs season), tuned to broadcast-style relevance.
COLD_EFG_GAP = 0.03
TOV_TREND_GAP = 2.5
FORM_PM_GAP = 5.0


def zone_bucket(shot_zone_basic: str) -> str | None:
    """Design zone bucket for a SHOT_ZONE_BASIC value (None = not charted)."""
    return _ZONE_BUCKETS.get(shot_zone_basic)


def overview_flags(games: pd.DataFrame, window: int = 5) -> list[dict]:
    """Tactical flags from the last ``window`` games vs the season baseline.

    Parameters
    ----------
    games:
        Per-game rows ordered chronologically with OFF_EFG, OFF_TOV_PCT and
        PLUS_MINUS columns (``team_identity.team_game_factors`` output).

    Returns
    -------
    Flags as dicts with rule / severity (HIGH, MED, LOW) / message; a single
    LOW "all clear" flag when nothing stands out.
    """
    flags: list[dict] = []
    if len(games) <= window:
        return [
            {
                "rule": "sample",
                "severity": "LOW",
                "message": "Not enough games for last-5 trend analysis yet.",
            }
        ]

    season, last = games.iloc[:-window], games.tail(window)

    efg_gap = float(season["OFF_EFG"].mean() - last["OFF_EFG"].mean())
    if efg_gap >= COLD_EFG_GAP:
        flags.append(
            {
                "rule": "cold_shooting",
                "severity": "HIGH" if efg_gap >= 0.05 else "MED",
                "message": (
                    f"Shooting cold: eFG% {last['OFF_EFG'].mean():.1%} over the last "
                    f"{window} vs {season['OFF_EFG'].mean():.1%} season baseline."
                ),
            }
        )

    tov_gap = float(last["OFF_TOV_PCT"].mean() - season["OFF_TOV_PCT"].mean())
    if tov_gap >= TOV_TREND_GAP:
        flags.append(
            {
                "rule": "turnover_trend",
                "severity": "MED" if tov_gap < 4.0 else "HIGH",
                "message": (
                    f"TOV% trending up: {last['OFF_TOV_PCT'].mean():.1f}% vs "
                    f"{season['OFF_TOV_PCT'].mean():.1f}% season average."
                ),
            }
        )

    pm_gap = float(season["PLUS_MINUS"].mean() - last["PLUS_MINUS"].mean())
    if pm_gap >= FORM_PM_GAP:
        flags.append(
            {
                "rule": "form_dip",
                "severity": "MED",
                "message": (
                    f"Form dip: {last['PLUS_MINUS'].mean():+.1f} avg margin in the last "
                    f"{window} vs {season['PLUS_MINUS'].mean():+.1f} on the season."
                ),
            }
        )

    if not flags:
        flags.append(
            {
                "rule": "all_clear",
                "severity": "LOW",
                "message": f"Last {window} games in line with the season baseline.",
            }
        )
    return flags


def conference_standing(
    ratings: pd.DataFrame,
    teams: pd.DataFrame,
    team_id: int,
) -> tuple[int, str]:
    """(rank, conference) of a team by wins within its conference.

    Parameters
    ----------
    ratings:
        One row per team with TEAM_ID and W (e.g. ``league_ratings``).
    teams:
        The teams table (team_id, abbreviation).
    team_id:
        Team to rank.
    """
    merged = ratings.merge(teams, left_on="TEAM_ID", right_on="team_id")
    merged["conference"] = merged["abbreviation"].map(lambda a: "WEST" if a in _WEST else "EAST")
    row = merged.loc[merged["TEAM_ID"] == team_id].iloc[0]
    conference = str(row["conference"])
    peers = merged.loc[merged["conference"] == conference]
    rank = int((peers["W"] > row["W"]).sum()) + 1
    return rank, conference
