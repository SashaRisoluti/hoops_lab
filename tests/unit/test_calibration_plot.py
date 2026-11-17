"""Reliability table and Brier score behind scripts/calibration_plot.py."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.calibration_plot import brier_score, reliability_table


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
