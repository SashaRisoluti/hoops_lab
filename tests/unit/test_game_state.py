"""Unit tests for the live GameState reducer (exact hand-computed values)."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.live.game_state import GameState

HOME, AWAY = 10, 20


def _ev(
    n: int,
    action: str,
    team: int = 0,
    sub: str = "",
    score: tuple[int, int] | None = None,
    shot_value: int = 2,
    clock: str = "PT06M00.00S",
    description: str = "",
) -> dict:
    return {
        "gameId": "g1",
        "actionNumber": n,
        "period": 1,
        "clock": clock,
        "teamId": team,
        "location": "h" if team == HOME else ("v" if team == AWAY else ""),
        "actionType": action,
        "subType": sub,
        "shotValue": shot_value,
        "description": description,
        "scoreHome": str(score[0]) if score else "",
        "scoreAway": str(score[1]) if score else "",
    }


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _ev(1, "period", sub="start", clock="PT12M00.00S"),
            _ev(2, "Made Shot", HOME, "Jump Shot", score=(2, 0), clock="PT11M00.00S"),
            _ev(3, "Missed Shot", AWAY, "Jump Shot", shot_value=3, clock="PT10M30.00S"),
            _ev(4, "Rebound", HOME, "Unknown", clock="PT10M28.00S"),
            _ev(5, "Turnover", HOME, "Bad Pass", clock="PT09M00.00S"),
            _ev(6, "Made Shot", AWAY, "Jump Shot", score=(2, 3), shot_value=3, clock="PT02M00.00S"),
        ]
    )


def test_game_state_counts_and_score() -> None:
    state = GameState.from_events(_events(), home_id=HOME, away_id=AWAY)

    assert state.score == (2, 3)
    assert state.period == 1
    home = state.team_stats[HOME]
    away = state.team_stats[AWAY]
    assert (home.fgm, home.fga) == (1, 1)
    assert (away.fgm, away.fga, away.fg3m, away.fg3a) == (1, 2, 1, 2)
    assert away.efg_pct == pytest.approx((1 + 0.5 * 1) / 2)  # 0.75
    assert home.tov == 1


def test_game_state_possessions_and_ppp() -> None:
    state = GameState.from_events(_events(), home_id=HOME, away_id=AWAY)

    assert state.possession_count(HOME) == 2  # made FG + turnover
    assert state.possession_count(AWAY) == 2  # def-rebound miss + made three
    assert state.ppp(HOME) == pytest.approx(1.0)  # 2 points / 2 trips
    assert state.ppp(AWAY) == pytest.approx(1.5)  # 3 points / 2 trips


def test_game_state_pace_estimate() -> None:
    state = GameState.from_events(_events(), home_id=HOME, away_id=AWAY)

    # Last event at 2:00 of Q1 -> 10 minutes elapsed; 2 possessions per team.
    assert state.minutes_elapsed == pytest.approx(10.0)
    assert state.pace_estimate == pytest.approx(2.0 / 10.0 * 48.0)  # 9.6


def test_last_run_points_swing() -> None:
    state = GameState.from_events(_events(), home_id=HOME, away_id=AWAY)

    home_pts, away_pts = state.last_run(n=8)
    assert (home_pts, away_pts) == (2, 3)
