"""Unit tests for the Altair chart blocks.

Every builder takes an already-prepared DataFrame, returns a serializable
Altair chart and never touches the network or the database.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import pytest

from hoops_lab.visuals.altair_charts import (
    build_centroid_profile_chart,
    build_cluster_distribution_chart,
    build_four_factors_chart,
    build_recent_form_chart,
    build_shot_profile_chart,
    build_som_map_chart,
    build_team_percentile_chart,
)


def _assert_serializable_chart(chart: object) -> dict:
    assert isinstance(chart, alt.TopLevelMixin)
    spec = chart.to_dict()
    assert isinstance(spec, dict)
    assert "$schema" in spec
    return spec


def test_four_factors_chart() -> None:
    data = pd.DataFrame(
        {
            "factor": ["eFG%", "TOV%", "OREB%", "FTr"] * 2,
            "side": ["Mavericks"] * 4 + ["Opponent"] * 4,
            "value": [0.55, 12.1, 0.28, 0.24, 0.52, 13.4, 0.30, 0.22],
        }
    )
    spec = _assert_serializable_chart(build_four_factors_chart(data))
    # Inline data present (faceted specs move it under "datasets").
    values = spec.get("data", {}).get("values") or next(iter(spec.get("datasets", {}).values()))
    assert values


def test_team_percentile_chart_uses_tricolor() -> None:
    data = pd.DataFrame(
        {
            "metric": ["OFF rating", "DEF rating", "Pace"],
            "percentile": [80.0, 40.0, 10.0],
        }
    )
    spec = _assert_serializable_chart(build_team_percentile_chart(data))
    text = str(spec)
    assert "#16c47f" in text and "#ffd100" in text and "#e0262c" in text


def test_recent_form_chart() -> None:
    data = pd.DataFrame({"game": range(10), "value": [1.1] * 10})
    _assert_serializable_chart(build_recent_form_chart(data, title="Rolling NET"))


def test_shot_profile_chart() -> None:
    data = pd.DataFrame(
        {
            "zone": ["RIM", "PAINT", "MID", "CORNER 3", "ABOVE BREAK 3"],
            "frequency": [0.4, 0.15, 0.1, 0.1, 0.25],
            "fg_pct": [0.65, 0.45, 0.42, 0.39, 0.35],
        }
    )
    _assert_serializable_chart(build_shot_profile_chart(data))


def test_cluster_distribution_chart() -> None:
    data = pd.DataFrame({"label": ["Rim Pressure", "Corner Heavy"], "players": [40, 25]})
    _assert_serializable_chart(build_cluster_distribution_chart(data))


def test_centroid_profile_chart() -> None:
    data = pd.DataFrame(
        {
            "label": ["Rim Pressure"] * 3 + ["Corner Heavy"] * 3,
            "feature": ["rim_frequency", "midrange_frequency", "corner_three_frequency"] * 2,
            "value": [1.8, -0.3, -0.9, -1.1, 0.2, 2.0],
        }
    )
    _assert_serializable_chart(build_centroid_profile_chart(data))


def test_som_map_chart_with_highlight_and_jitter() -> None:
    coords = pd.DataFrame(
        {
            "player_id": [1, 2, 3, 4],
            "player_name": ["a", "b", "c", "d"],
            "team_id": [10, 10, 20, 20],
            "total_attempts": [200, 300, 150, 400],
            "som_x": [0, 0, 1, 2],  # two players share cell (0, 0)
            "som_y": [0, 0, 1, 2],
            "archetype": ["Rim", "Rim", "Corner", "Corner"],
        }
    )
    chart = build_som_map_chart(coords, grid_size=(3, 3), highlight_team_id=10)
    spec = _assert_serializable_chart(chart)
    values = spec.get("data", {}).get("values") or next(iter(spec.get("datasets", {}).values()))
    xs = [(v["som_x_jitter"], v["som_y_jitter"]) for v in values]
    assert len(set(xs)) == 4  # shared cells de-overlapped deterministically
    assert sum(v["highlighted"] for v in values) == 2


def test_som_map_chart_missing_columns_raise() -> None:
    with pytest.raises(ValueError, match="som_x"):
        build_som_map_chart(pd.DataFrame({"som_y": [0]}), grid_size=(2, 2))


def test_missing_columns_raise() -> None:
    with pytest.raises(ValueError, match="factor"):
        build_four_factors_chart(pd.DataFrame({"value": [1]}))
    with pytest.raises(ValueError, match="percentile"):
        build_team_percentile_chart(pd.DataFrame({"metric": ["x"]}))
    with pytest.raises(ValueError, match="zone"):
        build_shot_profile_chart(pd.DataFrame({"frequency": [1.0]}))
