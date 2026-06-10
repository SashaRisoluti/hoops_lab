"""Unit tests for the in-game win probability model."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hoops_lab.models.win_probability import build_game_states, predict_wp, train_win_probability

HOME, AWAY = 10, 20


def test_build_game_states_extracts_margin_and_time() -> None:
    events = pd.DataFrame(
        {
            "gameId": ["g1", "g1"],
            "actionNumber": [5, 9],
            "period": [1, 2],
            "clock": ["PT06M00.00S", "PT03M30.00S"],
            "teamId": [HOME, AWAY],
            "location": ["h", "v"],
            "actionType": ["Made Shot", "Made Shot"],
            "subType": ["Jump Shot", "Jump Shot"],
            "description": ["", ""],
            "scoreHome": ["10", "12"],
            "scoreAway": ["4", "11"],
        }
    )
    states = build_game_states(events, home_won={"g1": True})

    assert len(states) == 2
    first, second = states.iloc[0], states.iloc[1]
    assert first["margin"] == 6  # 10 - 4
    assert first["minutes_remaining"] == 48 - 6  # Q1, 6:00 left
    assert second["margin"] == 1
    assert second["minutes_remaining"] == 48 - (12 + 8.5)
    assert bool(first["home_won"]) is True


def _synthetic_states(n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    margins = rng.integers(-20, 21, n)
    minutes = rng.uniform(0.5, 47.5, n)
    # Ground truth: the leading team wins, ties are a coin flip.
    won = np.where(margins > 0, True, np.where(margins < 0, False, rng.random(n) < 0.5))
    return pd.DataFrame({"margin": margins, "minutes_remaining": minutes, "home_won": won})


def test_model_is_monotonic_in_margin_and_time() -> None:
    model = train_win_probability(_synthetic_states())

    assert predict_wp(model, margin=10, minutes_remaining=5) > predict_wp(
        model, margin=0, minutes_remaining=5
    )
    assert predict_wp(model, margin=0, minutes_remaining=5) > predict_wp(
        model, margin=-10, minutes_remaining=5
    )
    # The same lead is worth more with less time on the clock.
    assert predict_wp(model, margin=5, minutes_remaining=2) > predict_wp(
        model, margin=5, minutes_remaining=40
    )
    # Probabilities live in (0, 1).
    assert 0.0 < predict_wp(model, margin=-30, minutes_remaining=1) < 1.0
