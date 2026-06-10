"""Unit tests for the shot quality model (synthetic, deterministic signal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hoops_lab.models.shot_quality_model import score_shots, temporal_split, train_shot_quality


def _shots() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = pd.DataFrame(
        {
            "SHOT_DISTANCE": rng.uniform(0, 4, 100),
            "SHOT_TYPE": ["2PT Field Goal"] * 100,
            "SHOT_ZONE_BASIC": ["Restricted Area"] * 100,
            "PERIOD": rng.integers(1, 5, 100),
            "SHOT_MADE_FLAG": [1] * 80 + [0] * 20,
            "season": ["2023-24"] * 100,
        }
    )
    far = pd.DataFrame(
        {
            "SHOT_DISTANCE": rng.uniform(24, 28, 100),
            "SHOT_TYPE": ["3PT Field Goal"] * 100,
            "SHOT_ZONE_BASIC": ["Above the Break 3"] * 100,
            "PERIOD": rng.integers(1, 5, 100),
            "SHOT_MADE_FLAG": [1] * 20 + [0] * 80,
            "season": ["2024-25"] * 100,
        }
    )
    return pd.concat([close, far], ignore_index=True)


def test_model_learns_distance_signal_and_scores() -> None:
    shots = _shots()
    model = train_shot_quality(shots)
    scored = score_shots(model, shots)

    assert {"XFG", "XPTS"} <= set(scored.columns)
    close_xfg = scored.loc[scored["SHOT_DISTANCE"] < 5, "XFG"].mean()
    far_xfg = scored.loc[scored["SHOT_DISTANCE"] > 20, "XFG"].mean()
    assert close_xfg > far_xfg + 0.2  # the signal is unmistakable

    # Expected points weigh threes: XPTS = XFG * shot value.
    three_rows = scored.loc[scored["SHOT_TYPE"] == "3PT Field Goal"]
    assert np.allclose(three_rows["XPTS"], three_rows["XFG"] * 3.0)


def test_temporal_split_by_season() -> None:
    shots = _shots()
    train, test = temporal_split(shots, test_season="2024-25")

    assert set(train["season"]) == {"2023-24"}
    assert set(test["season"]) == {"2024-25"}
    assert len(train) + len(test) == len(shots)
