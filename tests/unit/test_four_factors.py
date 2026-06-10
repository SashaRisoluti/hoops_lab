"""Unit tests for offensive/defensive Four Factors (exact hand-computed values)."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.features.four_factors import FACTOR_DIRECTIONS, FACTOR_LABELS, four_factors


def _row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FGM": [40.0],
            "FG3M": [10.0],
            "FGA": [80.0],
            "FTA": [20.0],
            "FTM": [16.0],
            "TOV": [12.0],
            "OREB": [10.0],
            "DREB": [30.0],
            "OPP_FGM": [35.0],
            "OPP_FG3M": [8.0],
            "OPP_FGA": [85.0],
            "OPP_FTA": [25.0],
            "OPP_FTM": [20.0],
            "OPP_TOV": [15.0],
            "OPP_OREB": [12.0],
            "OPP_DREB": [33.0],
        }
    )


def test_offensive_four_factors() -> None:
    out = four_factors(_row()).iloc[0]
    assert out["OFF_EFG"] == pytest.approx(0.5625)  # (40 + 5) / 80
    assert out["OFF_TOV_PCT"] == pytest.approx(11.904762, abs=1e-5)  # 1200 / 100.8
    assert out["OFF_ORB_PCT"] == pytest.approx(23.255814, abs=1e-5)  # 1000 / 43
    assert out["OFF_FT_RATE"] == pytest.approx(0.2)  # 16 / 80


def test_defensive_four_factors_use_opponent_counts() -> None:
    out = four_factors(_row()).iloc[0]
    assert out["DEF_EFG"] == pytest.approx(0.458824, abs=1e-5)  # 39 / 85
    assert out["DEF_TOV_PCT"] == pytest.approx(13.513514, abs=1e-5)  # 1500 / 111
    assert out["DEF_ORB_PCT"] == pytest.approx(28.571429, abs=1e-5)  # 1200 / 42
    assert out["DEF_FT_RATE"] == pytest.approx(0.235294, abs=1e-5)  # 20 / 85


def test_direction_and_label_registries_cover_all_factors() -> None:
    out = four_factors(_row())
    factor_cols = [c for c in out.columns if c.startswith(("OFF_", "DEF_"))]
    assert set(FACTOR_DIRECTIONS) == set(factor_cols)
    assert set(FACTOR_LABELS) == set(factor_cols)
    # Forcing opponent turnovers is good; conceding offensive boards is not.
    assert FACTOR_DIRECTIONS["DEF_TOV_PCT"] is True
    assert FACTOR_DIRECTIONS["DEF_ORB_PCT"] is False
