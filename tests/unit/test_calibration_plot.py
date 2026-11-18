"""Reliability table and Brier score behind scripts/calibration_plot.py."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hoops_lab.models.game_win_probability import expected_calibration_error
from scripts.calibration_plot import (
    brier_score,
    choose_calibrator,
    cluster_bootstrap_ece,
    fit_calibrators,
    pick_calibrator,
    reliability_table,
    whole_season_game_ids,
)


def test_reliability_table_equal_count_bins() -> None:
    p = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    y = np.array([0, 0, 1, 0, 1, 1, 0, 1])

    table = reliability_table(y, p, bins=4)

    assert table["n"].tolist() == [2, 2, 2, 2]
    assert table["predicted"].tolist() == pytest.approx([0.15, 0.35, 0.65, 0.85])
    assert table["observed"].tolist() == pytest.approx([0.0, 0.5, 1.0, 0.5])


def test_reliability_table_splits_ties_into_equal_bins() -> None:
    # Saturated predictions (many identical p) must still fill every bin.
    p = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0])
    y = np.array([0, 0, 0, 1, 1, 1])

    table = reliability_table(y, p, bins=3)

    assert table["n"].tolist() == [2, 2, 2]
    assert table["observed"].tolist() == pytest.approx([0.0, 0.5, 1.0])


def test_brier_score_hand_computed() -> None:
    # (0.1-0)^2 + (0.8-1)^2 + (0.5-1)^2 = 0.01 + 0.04 + 0.25 = 0.30 -> mean 0.10
    assert brier_score(np.array([0, 1, 1]), np.array([0.1, 0.8, 0.5])) == pytest.approx(0.10)


def _miscalibrated(n: int = 6000, scale: float = 2.0, seed: int = 0):
    """Logits ``z`` whose true probability is sigmoid(scale * z): under-confident by ``scale``."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, 1.0, n)
    y = (rng.random(n) < 1.0 / (1.0 + np.exp(-scale * z))).astype(int)
    groups = np.arange(n) // 20  # 20 states per "game"
    return z, y, groups


def test_temperature_recovers_known_scale() -> None:
    z, y, _ = _miscalibrated(n=20000, scale=2.0)

    calibrators = fit_calibrators(z, y)

    p = calibrators["temperature"](np.array([0.0, 1.0]))
    assert p[0] == pytest.approx(0.5)
    # sigmoid(2 * 1) = 0.881; recovered within sampling noise
    assert p[1] == pytest.approx(0.881, abs=0.02)


def test_pick_keeps_none_unless_a_calibrator_beats_it() -> None:
    cv = pd.DataFrame({"brier": [0.150, 0.151, 0.153]}, index=["none", "temperature", "platt"])
    assert pick_calibrator(cv) == "none"

    cv.loc["platt", "brier"] = 0.149
    assert pick_calibrator(cv) == "platt"


def test_choose_calibrator_fixes_strong_miscalibration() -> None:
    z, y, groups = _miscalibrated()

    chosen, cv = choose_calibrator(z, y, groups)

    assert set(cv.index) == {"none", "temperature", "platt", "isotonic"}
    assert chosen != "none"
    assert cv.loc[chosen, "brier"] < cv.loc["none", "brier"]


def test_cluster_bootstrap_interval_brackets_point_estimate() -> None:
    z, y, groups = _miscalibrated(n=2000)
    p = 1.0 / (1.0 + np.exp(-z))

    lo, hi = cluster_bootstrap_ece(y, p, groups, n_boot=200)

    assert 0.0 <= lo < expected_calibration_error(y, p) < hi


def test_whole_season_game_ids_is_the_seeded_regular_season_sample(tmp_path: Path) -> None:
    regular = [f"00225{i:05d}" for i in range(300)]
    playoffs = [f"00425{i:05d}" for i in range(10)]
    pd.DataFrame({"GAME_ID": (regular + playoffs) * 2}).to_parquet(
        tmp_path / "team_box_2025-26.parquet"
    )

    ids = whole_season_game_ids("2025-26", tmp_path)

    assert len(ids) == 250
    assert ids <= set(regular)
    assert ids == whole_season_game_ids("2025-26", tmp_path)
