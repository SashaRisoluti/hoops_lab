"""Unit tests for dynamic percentiles, z-scores and the filter hash."""

from __future__ import annotations

import pandas as pd
import pytest

from hoops_lab.features.percentiles import (
    add_stat_percentiles,
    filter_hash,
    percentile_rank,
    z_score,
)


def test_percentile_rank_exact_values() -> None:
    series = pd.Series([10.0, 20.0, 30.0, 40.0])
    assert percentile_rank(series).tolist() == [25.0, 50.0, 75.0, 100.0]


def test_z_score_population_std() -> None:
    series = pd.Series([10.0, 20.0, 30.0, 40.0])  # mean 25, std (ddof=0) = sqrt(125)
    z = z_score(series)
    assert z.iloc[2] == pytest.approx(0.4472136, abs=1e-6)
    assert z.iloc[0] == pytest.approx(-1.3416408, abs=1e-6)


def test_add_stat_percentiles_adds_pctl_z_rank() -> None:
    df = pd.DataFrame({"PTS": [10.0, 20.0, 30.0, 40.0]})
    out = add_stat_percentiles(df, ["PTS"])

    assert out["PTS_PCTL"].tolist() == [25.0, 50.0, 75.0, 100.0]
    assert out["PTS_RANK"].tolist() == [4, 3, 2, 1]  # rank 1 = best (highest value)
    assert out["PTS_Z"].iloc[3] == pytest.approx(1.3416408, abs=1e-6)
    assert "PTS_PCTL" not in df.columns  # input must not be mutated


def test_filter_hash_is_order_insensitive_and_value_sensitive() -> None:
    base = {"role": "Guard", "min_mpg": 25, "seasons": ["2023-24", "2024-25"]}
    reordered = {"seasons": ["2023-24", "2024-25"], "min_mpg": 25, "role": "Guard"}
    changed = {"role": "Guard", "min_mpg": 30, "seasons": ["2023-24", "2024-25"]}

    assert filter_hash(base) == filter_hash(reordered)
    assert filter_hash(base) != filter_hash(changed)
    assert isinstance(filter_hash(base), str)
    assert len(filter_hash(base)) == 16
