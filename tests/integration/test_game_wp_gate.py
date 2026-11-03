"""Quality gate of the drifting-lead win-probability model on a temporal holdout."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH
from hoops_lab.models.game_win_probability import evaluate_holdout, gate_passes
from hoops_lab.storage.database import Database
from scripts.export_web_data import build_win_probability

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)

METRIC_KEYS = {
    "trainGames",
    "holdoutGames",
    "holdoutLogLoss",
    "baselineLogLoss",
    "ece",
    "pregameLogLoss",
    "constantLogLoss",
}


def test_drifting_lead_model_passes_the_gate_on_held_out_seasons() -> None:
    metrics = evaluate_holdout(Database())
    print(f"\nwin-probability gate metrics: {metrics}")

    assert set(metrics) == METRIC_KEYS
    assert metrics["trainGames"] > 0 and metrics["holdoutGames"] > 0
    assert gate_passes(metrics), metrics


def test_exported_model_has_the_contract_shape() -> None:
    model = build_win_probability(Database())

    assert model["available"] is True
    assert set(model) == {
        "available",
        "coefficients",
        "homeCourtPts",
        "pointsPerNetRating",
        "scale",
        "k",
        "season",
        "asOf",
        "teams",
        "metrics",
    }
    assert set(model["coefficients"]) == {"a", "b", "c"}
    assert set(model["metrics"]) == METRIC_KEYS
    assert len(model["teams"]) == 30
    assert all(len(tricode) == 3 for tricode in model["teams"])
