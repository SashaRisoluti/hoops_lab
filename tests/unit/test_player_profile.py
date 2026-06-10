"""Unit tests for the player profile analytics (radar + lineup-based on/off)."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.analytics.player_profile import (
    RADAR_CATEGORIES,
    player_on_off,
    radar_percentiles,
)
from hoops_lab.storage.database import Database


def _population() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "PTS": [10.0, 20.0, 30.0, 40.0],
            "TS_PCT": [0.50, 0.55, 0.60, 0.65],
            "AST_PCT": [0.10, 0.20, 0.30, 0.40],
            "REB_PCT": [0.05, 0.10, 0.15, 0.20],
            "DEF_RATING": [110.0, 108.0, 106.0, 104.0],  # lower = better
            "USG_PCT": [0.15, 0.20, 0.25, 0.30],
        }
    )


def test_radar_percentiles_best_row_scores_100_everywhere() -> None:
    values = radar_percentiles(_population(), row_idx=3)
    # Row 3 is best in every category, including defense (lowest DEF_RATING).
    assert values["Scoring"] == 100.0
    assert values["Defense"] == 100.0
    assert set(values) == set(RADAR_CATEGORIES)


def test_radar_percentiles_inverts_lower_is_better() -> None:
    values = radar_percentiles(_population(), row_idx=0)
    assert values["Scoring"] == 25.0
    assert values["Defense"] == 25.0  # worst defense (110) -> bottom percentile


def test_radar_percentiles_skips_missing_columns() -> None:
    population = _population().drop(columns=["USG_PCT"])
    values = radar_percentiles(population, row_idx=2)
    assert "Usage" not in values
    assert "Scoring" in values


def _on_off_db() -> Database:
    db = Database(path=":memory:")
    con = db.connect()

    lineups = pd.DataFrame(
        {
            "season": ["2023-24"] * 3,
            "TEAM_ID": [5, 5, 5],
            "GROUP_ID": ["-99-2-3-4-5-", "-99-6-7-8-9-", "-1-2-3-4-5-"],
            "MIN": [60.0, 36.0, 144.0],
            "PLUS_MINUS": [18.0, -6.0, -6.0],
        }
    )
    con.register("lineups", lineups)

    team_box = pd.DataFrame(
        {
            "season": ["2023-24"] * 5,
            "TEAM_ID": [5] * 5,
            "MIN": [240] * 5,  # team-box minutes are player-minutes (clock x 5)
            "PLUS_MINUS": [2.0, 2.0, 2.0, 0.0, 0.0],
        }
    )
    con.register("box_scores_team", team_box)
    return db


def test_player_on_off_exact_arithmetic() -> None:
    result = player_on_off(_on_off_db(), player_id=99, team_id=5, season="2023-24")

    assert result is not None
    # ON: 96 clock minutes, +12 -> +6.0 per 48.
    assert result["on_min"] == pytest.approx(96.0)
    assert result["on_pm_per48"] == pytest.approx(6.0)
    # Team: 1200/5 = 240 clock minutes, +6 -> OFF: 144 min, -6 -> -2.0 per 48.
    assert result["off_min"] == pytest.approx(144.0)
    assert result["off_pm_per48"] == pytest.approx(-2.0)
    assert result["on_off_per48"] == pytest.approx(8.0)


def test_player_on_off_does_not_match_substring_ids() -> None:
    # Player 9 appears only as part of ids -99- and -9...-: the LIKE pattern
    # must match the exact -9- token, which exists only in "-99-6-7-8-9-".
    result = player_on_off(_on_off_db(), player_id=9, team_id=5, season="2023-24")
    assert result is not None
    assert result["on_min"] == pytest.approx(36.0)


def test_player_on_off_returns_none_without_lineup_minutes() -> None:
    assert player_on_off(_on_off_db(), player_id=12345, team_id=5, season="2023-24") is None
