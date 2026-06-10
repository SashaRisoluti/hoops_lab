"""Unit tests for advanced shooting/playmaking stats (exact hand-computed values)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from hoops_lab.features.advanced import (
    add_advanced_stats,
    assist_to_turnover,
    effective_fg_pct,
    free_throw_rate,
    three_point_attempt_rate,
    true_shooting_pct,
    turnover_pct,
)


def test_true_shooting_pct_formula() -> None:
    # TS% = PTS / (2 * (FGA + 0.44 * FTA)) = 30 / 48.8
    df = pd.DataFrame({"PTS": [30.0], "FGA": [20.0], "FTA": [10.0]})
    out = true_shooting_pct(df)
    assert out["TS_PCT_CALC"].iloc[0] == pytest.approx(0.6147541, abs=1e-6)


def test_true_shooting_pct_no_attempts_yields_nan() -> None:
    df = pd.DataFrame({"PTS": [0.0], "FGA": [0.0], "FTA": [0.0]})
    out = true_shooting_pct(df)
    assert math.isnan(out["TS_PCT_CALC"].iloc[0])


def test_effective_fg_pct_formula() -> None:
    # eFG% = (FGM + 0.5 * FG3M) / FGA = (10 + 2) / 20
    df = pd.DataFrame({"FGM": [10.0], "FG3M": [4.0], "FGA": [20.0]})
    out = effective_fg_pct(df)
    assert out["EFG_PCT_CALC"].iloc[0] == pytest.approx(0.6)


def test_rates_and_ratios() -> None:
    df = pd.DataFrame({"FG3A": [8.0], "FGA": [20.0], "FTA": [10.0], "AST": [8.0], "TOV": [2.0]})
    assert three_point_attempt_rate(df)["FG3A_RATE_CALC"].iloc[0] == pytest.approx(0.4)
    assert free_throw_rate(df)["FTR_CALC"].iloc[0] == pytest.approx(0.5)
    assert assist_to_turnover(df)["AST_TO_CALC"].iloc[0] == pytest.approx(4.0)


def test_assist_to_turnover_zero_tov_yields_nan() -> None:
    df = pd.DataFrame({"AST": [5.0], "TOV": [0.0]})
    assert math.isnan(assist_to_turnover(df)["AST_TO_CALC"].iloc[0])


def test_turnover_pct_formula() -> None:
    # TOV% = 100 * TOV / (FGA + 0.44 * FTA + TOV) = 300 / 27.4
    df = pd.DataFrame({"TOV": [3.0], "FGA": [20.0], "FTA": [10.0]})
    out = turnover_pct(df)
    assert out["TOV_PCT_CALC"].iloc[0] == pytest.approx(10.948905, abs=1e-5)


def test_add_advanced_stats_applies_everything() -> None:
    df = pd.DataFrame(
        {
            "PTS": [30.0],
            "FGM": [10.0],
            "FGA": [20.0],
            "FG3M": [4.0],
            "FG3A": [8.0],
            "FTA": [10.0],
            "AST": [8.0],
            "TOV": [2.0],
        }
    )
    out = add_advanced_stats(df)
    for col in (
        "TS_PCT_CALC",
        "EFG_PCT_CALC",
        "FG3A_RATE_CALC",
        "FTR_CALC",
        "AST_TO_CALC",
        "TOV_PCT_CALC",
    ):
        assert col in out.columns
