"""Unit tests for the shot-zone efficiency aggregation (pure function)."""

from __future__ import annotations

import pandas as pd
import pytest

from dashboard.components.shot_chart import zone_efficiency


def test_zone_efficiency_weights_threes() -> None:
    shots = pd.DataFrame(
        {
            "SHOT_ZONE_BASIC": [
                "Restricted Area",
                "Restricted Area",
                "Above the Break 3",
                "Above the Break 3",
            ],
            "SHOT_TYPE": ["2PT Field Goal", "2PT Field Goal", "3PT Field Goal", "3PT Field Goal"],
            "SHOT_MADE_FLAG": [1, 0, 1, 0],
        }
    )
    zones = zone_efficiency(shots).set_index("SHOT_ZONE_BASIC")

    restricted = zones.loc["Restricted Area"]
    assert restricted["attempts"] == 2
    assert restricted["fg_pct"] == pytest.approx(0.5)
    assert restricted["pps"] == pytest.approx(1.0)  # 2 points / 2 attempts

    three = zones.loc["Above the Break 3"]
    assert three["fg_pct"] == pytest.approx(0.5)
    assert three["pps"] == pytest.approx(1.5)  # 3 points / 2 attempts
