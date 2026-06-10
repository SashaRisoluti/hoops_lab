"""Lineup analytics on the complete 5-man population.

Counting stats are additive across disjoint 5-man lineup rows, so 2/3/4-man
player combinations aggregate EXACTLY by summing every lineup containing the
combo — a direct payoff of downloading the complete per-team population.

Lineups carry own-team counts only (Base measure): offensive metrics
(ORtg estimate, eFG%, TS%, TOV%) are exact-from-counts, while defensive
ratings are not derivable — plus/minus per 48 remains the two-way signal.
"""

from __future__ import annotations

import itertools

import pandas as pd

from hoops_lab.features.advanced import effective_fg_pct, true_shooting_pct, turnover_pct
from hoops_lab.features.traditional import _safe_div, estimate_possessions

#: Columns that sum exactly when aggregating lineups into combinations.
SUM_COLS = ["MIN", "PTS", "FGM", "FGA", "FG3M", "FTA", "TOV", "OREB", "PLUS_MINUS"]


def parse_lineup_players(group_id: str) -> list[int]:
    """Player ids from a GROUP_ID like ``-1629029-203507-2544-``."""
    return [int(token) for token in str(group_id).split("-") if token.strip()]


def enrich_lineups(df: pd.DataFrame) -> pd.DataFrame:
    """Add possession estimate, ORtg estimate, shooting metrics and +/- per 48."""
    out = estimate_possessions(df.copy())
    out["ORTG_EST"] = _safe_div(100.0 * out["PTS"], out["POSS_EST"])
    out = effective_fg_pct(out)
    out = true_shooting_pct(out)
    out = turnover_pct(out)
    out["PM_PER48"] = _safe_div(out["PLUS_MINUS"] * 48.0, out["MIN"])
    return out


def filter_lineups_by_players(
    df: pd.DataFrame,
    with_ids: list[int] | None = None,
    without_ids: list[int] | None = None,
) -> pd.DataFrame:
    """Keep lineups containing every ``with_ids`` and none of ``without_ids``."""
    mask = pd.Series(True, index=df.index)
    for player_id in with_ids or []:
        mask &= df["GROUP_ID"].str.contains(f"-{player_id}-", regex=False)
    for player_id in without_ids or []:
        mask &= ~df["GROUP_ID"].str.contains(f"-{player_id}-", regex=False)
    return df.loc[mask]


def player_combinations(
    df: pd.DataFrame,
    size: int = 2,
    min_minutes: float = 50,
) -> pd.DataFrame:
    """Exact stats for every ``size``-player combination found in the lineups.

    Each 5-man row contributes its counts to all C(5, size) combinations it
    contains; summing across rows yields the combination's exact totals.
    """
    records: list[dict] = []
    for _, row in df.iterrows():
        ids = parse_lineup_players(row["GROUP_ID"])
        base = {col: row[col] for col in SUM_COLS if col in df.columns}
        for combo in itertools.combinations(sorted(ids), size):
            records.append({"players": combo, **base})

    if not records:
        return pd.DataFrame(columns=["players", *SUM_COLS])

    combos = pd.DataFrame(records).groupby("players", as_index=False).sum()
    combos = enrich_lineups(combos)
    combos = combos.loc[combos["MIN"] >= min_minutes]
    return combos.sort_values("PM_PER48", ascending=False).reset_index(drop=True)
