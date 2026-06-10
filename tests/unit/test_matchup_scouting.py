"""Unit tests for matchup leverage and the scouting strengths/weaknesses."""

from __future__ import annotations

import pandas as pd

from hoops_lab.analytics.matchup import matchup_leverage
from hoops_lab.analytics.opponent_scouting import strengths_weaknesses


def _league() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TEAM_ID": [1, 2],
            "TEAM_ABBREVIATION": ["AAA", "BBB"],
            "OFF_EFG": [0.56, 0.50],
            "OFF_TOV_PCT": [11.0, 14.0],
            "OFF_ORB_PCT": [30.0, 24.0],
            "OFF_FT_RATE": [0.20, 0.22],
            "DEF_EFG": [0.50, 0.55],
            "DEF_TOV_PCT": [14.0, 11.0],
            "DEF_ORB_PCT": [24.0, 30.0],
            "DEF_FT_RATE": [0.20, 0.25],
            "OFF_EFG_PCTL": [90.0, 40.0],
            "OFF_TOV_PCT_PCTL": [80.0, 30.0],
            "OFF_ORB_PCT_PCTL": [70.0, 20.0],
            "OFF_FT_RATE_PCTL": [50.0, 60.0],
            "DEF_EFG_PCTL": [85.0, 10.0],
            "DEF_TOV_PCT_PCTL": [75.0, 35.0],
            "DEF_ORB_PCT_PCTL": [65.0, 45.0],
            "DEF_FT_RATE_PCTL": [55.0, 25.0],
        }
    )


def test_matchup_leverage_ranks_biggest_edges_first() -> None:
    edges = matchup_leverage(_league(), team_a=1, team_b=2)

    # A attacks where it is strong AND B defends poorly:
    # eFG: (90 + (100 - 10)) / 2 = 90 -> must rank first.
    assert edges.iloc[0]["factor"] == "OFF_EFG"
    assert edges.iloc[0]["leverage"] == 90.0
    assert edges.iloc[0]["attacking_team"] == "AAA"
    # Both directions are evaluated (A offense vs B defense and vice versa).
    assert set(edges["attacking_team"]) == {"AAA", "BBB"}
    assert (edges["leverage"].diff().dropna() <= 0).all()  # sorted descending


def test_strengths_and_weaknesses_pick_extreme_percentiles() -> None:
    strengths, weaknesses = strengths_weaknesses(_league(), team_id=2, top_k=2)

    assert len(strengths) == 2 and len(weaknesses) == 2
    # Team 2's best percentile is OFF_FT_RATE (60), worst is DEF_EFG (10).
    assert "free-throw" in strengths[0].lower() or "ft" in strengths[0].lower()
    assert "efg" in weaknesses[0].lower() or "shooting" in weaknesses[0].lower()
