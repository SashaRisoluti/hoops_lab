"""Unit tests for traditional-stat normalisation (exact hand-computed values)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from hoops_lab.features.traditional import (
    estimate_possessions,
    per_36,
    per_100_possessions,
    per_game,
)


def test_per_game_divides_by_games_played() -> None:
    df = pd.DataFrame({"PTS": [100, 60], "GP": [4, 3]})
    out = per_game(df, ["PTS"])
    assert out["PTS_PG"].tolist() == [25.0, 20.0]
    assert "PTS_PG" not in df.columns  # input must not be mutated


def test_per_game_zero_games_yields_nan() -> None:
    df = pd.DataFrame({"PTS": [10], "GP": [0]})
    out = per_game(df, ["PTS"])
    assert math.isnan(out["PTS_PG"].iloc[0])


def test_per_36_scales_to_36_minutes() -> None:
    df = pd.DataFrame({"PTS": [30.0, 20.0], "MIN": [36.0, 18.0]})
    out = per_36(df, ["PTS"])
    assert out["PTS_PER36"].tolist() == [30.0, 40.0]


def test_estimate_possessions_classic_formula() -> None:
    # POSS ~= FGA + 0.44*FTA - OREB + TOV
    df = pd.DataFrame({"FGA": [80], "FTA": [25], "OREB": [10], "TOV": [15]})
    out = estimate_possessions(df)
    assert out["POSS_EST"].iloc[0] == pytest.approx(96.0)


def test_per_100_possessions() -> None:
    df = pd.DataFrame({"PTS": [110.0], "POSS_EST": [96.0]})
    out = per_100_possessions(df, ["PTS"])
    assert out["PTS_PER100"].iloc[0] == pytest.approx(114.5833, abs=1e-4)
