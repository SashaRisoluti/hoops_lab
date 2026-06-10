"""Dynamic percentiles and z-scores against a filtered population.

The population is whatever DataFrame you pass in: callers apply their filters
FIRST (minimum minutes, role, seasons, ...), then compute percentiles — per
the project rule that percentiles are always relative to the filtered
population, never the full universe. :func:`filter_hash` provides the stable
cache key used by the ``player_percentiles`` table.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd


def percentile_rank(series: pd.Series) -> pd.Series:
    """Percentile (0-100] of each value within the series (average-rank method)."""
    return series.rank(pct=True, method="average") * 100.0


def z_score(series: pd.Series) -> pd.Series:
    """Standard score using the population standard deviation (ddof=0)."""
    std = series.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(float("nan"), index=series.index)
    return (series - series.mean()) / std


def add_stat_percentiles(
    df: pd.DataFrame,
    cols: list[str],
    pctl_suffix: str = "_PCTL",
    z_suffix: str = "_Z",
    rank_suffix: str = "_RANK",
) -> pd.DataFrame:
    """Add percentile, z-score and rank columns for each requested stat.

    Rank 1 is the best (highest) value. The input DataFrame must already be
    filtered down to the comparison population.
    """
    out = df.copy()
    for col in cols:
        out[f"{col}{pctl_suffix}"] = percentile_rank(out[col])
        out[f"{col}{z_suffix}"] = z_score(out[col])
        out[f"{col}{rank_suffix}"] = out[col].rank(ascending=False, method="min").astype("Int64")
    return out


def filter_hash(filters: dict[str, Any]) -> str:
    """Stable 16-char key identifying a filter combination.

    Key order does not matter; values do. Used as ``population_filter_hash``
    in the ``player_percentiles`` cache table.
    """
    canonical = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()[:16]
