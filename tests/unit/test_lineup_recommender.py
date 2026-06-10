"""Unit tests for the shrinkage-based lineup recommender (exact values)."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.models.lineup_recommender import recommend_lineups


def test_shrinkage_favours_proven_minutes() -> None:
    lineups = pd.DataFrame(
        {
            "GROUP_NAME": ["proven", "small-sample"],
            "MIN": [100.0, 20.0],
            "PLUS_MINUS": [24.0, 10.0],
        }
    )
    ranked = recommend_lineups(lineups, top_n=2, prior_minutes=96)

    # Raw +/- per 48 would rank the 20-minute lineup first (24.0 vs 11.5);
    # shrinkage toward zero flips it: 24/(100+96)*48 vs 10/(20+96)*48.
    assert ranked.iloc[0]["GROUP_NAME"] == "proven"
    assert ranked.iloc[0]["PM_PER48_SHRUNK"] == pytest.approx(24.0 / 196.0 * 48.0)
    assert ranked.iloc[1]["PM_PER48_SHRUNK"] == pytest.approx(10.0 / 116.0 * 48.0)


def test_top_n_limits_results() -> None:
    lineups = pd.DataFrame(
        {
            "GROUP_NAME": [f"l{i}" for i in range(10)],
            "MIN": [50.0] * 10,
            "PLUS_MINUS": list(range(10)),
        }
    )
    assert len(recommend_lineups(lineups, top_n=3)) == 3
