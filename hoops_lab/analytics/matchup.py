"""Head-to-head comparison and the (adapted) Matchup Leverage Index.

The spec's leverage formula weighs play-type frequency x efficiency x
opponent weakness; play-type data is not ingested yet, so the MVP version
scores each offensive Four Factor of one team against the opposing team's
corresponding defensive factor:

    leverage = (attacker offensive pctl + (100 - defender defensive pctl)) / 2

100 means "attack here": the attacker excels exactly where the defender is
weakest. The play-type-weighted version lands with the possession data.
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.four_factors import FACTOR_LABELS

#: offensive factor -> the defensive factor that resists it.
_OFF_TO_DEF = {
    "OFF_EFG": "DEF_EFG",
    "OFF_TOV_PCT": "DEF_TOV_PCT",
    "OFF_ORB_PCT": "DEF_ORB_PCT",
    "OFF_FT_RATE": "DEF_FT_RATE",
}


def matchup_leverage(league: pd.DataFrame, team_a: int, team_b: int) -> pd.DataFrame:
    """Rank the tactical opportunities between two teams (both directions).

    Parameters
    ----------
    league:
        Output of ``team_identity.league_team_factors``.
    team_a / team_b:
        TEAM_IDs to compare.

    Returns
    -------
    One row per (attacking team, offensive factor), sorted by descending
    leverage score.
    """
    rows = []
    teams = {
        team_a: league.loc[league["TEAM_ID"] == team_a].iloc[0],
        team_b: league.loc[league["TEAM_ID"] == team_b].iloc[0],
    }
    for attacker_id, defender_id in ((team_a, team_b), (team_b, team_a)):
        attacker, defender = teams[attacker_id], teams[defender_id]
        for off_factor, def_factor in _OFF_TO_DEF.items():
            off_pctl = float(attacker[f"{off_factor}_PCTL"])
            def_pctl = float(defender[f"{def_factor}_PCTL"])
            rows.append(
                {
                    "attacking_team": attacker["TEAM_ABBREVIATION"],
                    "factor": off_factor,
                    "label": FACTOR_LABELS[off_factor],
                    "attacker_pctl": off_pctl,
                    "defender_pctl": def_pctl,
                    "leverage": (off_pctl + (100.0 - def_pctl)) / 2.0,
                }
            )
    return pd.DataFrame(rows).sort_values("leverage", ascending=False).reset_index(drop=True)


def matchup_table(league: pd.DataFrame, team_a: int, team_b: int) -> pd.DataFrame:
    """Side-by-side Four Factors with the edge holder per row."""
    a = league.loc[league["TEAM_ID"] == team_a].iloc[0]
    b = league.loc[league["TEAM_ID"] == team_b].iloc[0]
    rows = []
    for factor, label in FACTOR_LABELS.items():
        a_pctl, b_pctl = float(a[f"{factor}_PCTL"]), float(b[f"{factor}_PCTL"])
        rows.append(
            {
                "factor": label,
                str(a["TEAM_ABBREVIATION"]): float(a[factor]),
                str(b["TEAM_ABBREVIATION"]): float(b[factor]),
                "edge": str(a["TEAM_ABBREVIATION"])
                if a_pctl >= b_pctl
                else str(b["TEAM_ABBREVIATION"]),
            }
        )
    return pd.DataFrame(rows)
