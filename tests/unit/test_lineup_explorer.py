"""Unit tests for lineup enrichment, player filters and exact combinations."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.analytics.lineup_explorer import (
    enrich_lineups,
    filter_lineups_by_players,
    parse_lineup_players,
    player_combinations,
)


def _lineups() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "GROUP_ID": ["-1-2-3-4-5-", "-1-2-3-4-6-"],
            "MIN": [100.0, 50.0],
            "PTS": [212.0, 90.0],
            "FGM": [80.0, 34.0],
            "FGA": [160.0, 80.0],
            "FG3M": [20.0, 10.0],
            "FTA": [50.0, 20.0],
            "TOV": [24.0, 13.0],
            "OREB": [20.0, 8.8],
            "PLUS_MINUS": [24.0, -12.0],
        }
    )


def test_parse_lineup_players() -> None:
    assert parse_lineup_players("-1629029-203507-2544-") == [1629029, 203507, 2544]


def test_enrich_lineups_exact_values() -> None:
    row = enrich_lineups(_lineups()).iloc[0]
    # POSS = 160 + 0.44*50 - 20 + 24 = 186 ; ORTG_EST = 100*212/186
    assert row["POSS_EST"] == pytest.approx(186.0)
    assert row["ORTG_EST"] == pytest.approx(113.978495, abs=1e-5)
    assert row["PM_PER48"] == pytest.approx(24.0 / 100.0 * 48.0)
    assert row["EFG_PCT_CALC"] == pytest.approx((80 + 10) / 160)


def test_filter_lineups_with_and_without_players() -> None:
    lineups = _lineups()

    with_six = filter_lineups_by_players(lineups, with_ids=[1, 6])
    assert with_six["GROUP_ID"].tolist() == ["-1-2-3-4-6-"]

    without_six = filter_lineups_by_players(lineups, without_ids=[6])
    assert without_six["GROUP_ID"].tolist() == ["-1-2-3-4-5-"]


def test_player_combinations_aggregate_exactly() -> None:
    combos = player_combinations(_lineups(), size=2, min_minutes=0)

    pair_12 = combos.loc[combos["players"] == (1, 2)].iloc[0]
    assert pair_12["MIN"] == pytest.approx(150.0)  # both lineups
    assert pair_12["PLUS_MINUS"] == pytest.approx(12.0)  # +24 - 12
    assert pair_12["PM_PER48"] == pytest.approx(12.0 / 150.0 * 48.0)

    pair_46 = combos.loc[combos["players"] == (4, 6)].iloc[0]
    assert pair_46["MIN"] == pytest.approx(50.0)  # second lineup only
    assert pair_46["PM_PER48"] == pytest.approx(-12.0 / 50.0 * 48.0)

    # C(5,2)=10 pairs per lineup; the 4 shared players share C(4,2)=6 pairs
    # -> 10 + 10 - 6 = 14 distinct pairs.
    assert len(combos) == 14


def test_player_combinations_respect_min_minutes() -> None:
    combos = player_combinations(_lineups(), size=2, min_minutes=120)
    # Only pairs present in both lineups reach 150 minutes.
    assert set(combos["players"]) == {(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)}
