"""Offensive and defensive Four Factors (Dean Oliver).

Input frames must carry the team's counting stats plus the opponent's with
an ``OPP_`` prefix (see ``analytics.team_identity.team_game_factors`` for the
self-join that produces them). Percentages are 0-1 fractions except the
turnover/rebound shares, expressed 0-100 like nba_api does.
"""

from __future__ import annotations

import pandas as pd

from hoops_lab.features.traditional import FT_POSSESSION_WEIGHT, _safe_div

#: factor column -> True when higher is better (drives percentile inversion).
FACTOR_DIRECTIONS: dict[str, bool] = {
    "OFF_EFG": True,
    "OFF_TOV_PCT": False,
    "OFF_ORB_PCT": True,
    "OFF_FT_RATE": True,
    "DEF_EFG": False,
    "DEF_TOV_PCT": True,  # forcing opponent turnovers is good
    "DEF_ORB_PCT": False,  # conceding offensive boards is bad
    "DEF_FT_RATE": False,
}

#: factor column -> human-readable label for reports and UI.
FACTOR_LABELS: dict[str, str] = {
    "OFF_EFG": "Shooting (eFG%)",
    "OFF_TOV_PCT": "Ball security (TOV%)",
    "OFF_ORB_PCT": "Offensive rebounding (ORB%)",
    "OFF_FT_RATE": "Free-throw rate (FT/FGA)",
    "DEF_EFG": "Shooting defense (opp. eFG%)",
    "DEF_TOV_PCT": "Forcing turnovers (opp. TOV%)",
    "DEF_ORB_PCT": "Defensive glass (opp. ORB%)",
    "DEF_FT_RATE": "Foul discipline (opp. FT/FGA)",
}


def four_factors(df: pd.DataFrame, opp_prefix: str = "OPP_") -> pd.DataFrame:
    """Add the eight Four Factors columns to a counts DataFrame (copy).

    Offensive factors use the team's own counts; defensive factors use the
    opponent's (``OPP_``-prefixed) counts against the team's defensive
    rebounds.
    """
    out = df.copy()
    opp = lambda col: out[f"{opp_prefix}{col}"]  # noqa: E731

    out["OFF_EFG"] = _safe_div(out["FGM"] + 0.5 * out["FG3M"], out["FGA"])
    out["OFF_TOV_PCT"] = _safe_div(
        100.0 * out["TOV"], out["FGA"] + FT_POSSESSION_WEIGHT * out["FTA"] + out["TOV"]
    )
    out["OFF_ORB_PCT"] = _safe_div(100.0 * out["OREB"], out["OREB"] + opp("DREB"))
    out["OFF_FT_RATE"] = _safe_div(out["FTM"], out["FGA"])

    out["DEF_EFG"] = _safe_div(opp("FGM") + 0.5 * opp("FG3M"), opp("FGA"))
    out["DEF_TOV_PCT"] = _safe_div(
        100.0 * opp("TOV"), opp("FGA") + FT_POSSESSION_WEIGHT * opp("FTA") + opp("TOV")
    )
    out["DEF_ORB_PCT"] = _safe_div(100.0 * opp("OREB"), opp("OREB") + out["DREB"])
    out["DEF_FT_RATE"] = _safe_div(opp("FTM"), opp("FGA"))
    return out
