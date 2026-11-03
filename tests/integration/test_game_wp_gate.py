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

#: Frozen split: the two newest completed seasons held out, the three before them trained.
TRAIN_SEASONS = ["2021-22", "2022-23", "2023-24"]
HELD_OUT_SEASONS = ["2024-25", "2025-26"]


def _pbp_games(db: Database, seasons: list[str]) -> int:
    marks = ", ".join("?" for _ in seasons)
    row = db.fetchone(
        f"SELECT COUNT(DISTINCT gameId) FROM play_by_play WHERE season IN ({marks})", seasons
    )
    return int(row[0]) if row else 0


def test_drifting_lead_model_passes_the_gate_on_held_out_seasons() -> None:
    db = Database()
    metrics = evaluate_holdout(db, HELD_OUT_SEASONS)
    print(f"\nwin-probability gate metrics (held out {HELD_OUT_SEASONS}): {metrics}")

    assert set(metrics) == METRIC_KEYS
    assert metrics["trainGames"] == _pbp_games(db, TRAIN_SEASONS)
    assert metrics["holdoutGames"] == _pbp_games(db, HELD_OUT_SEASONS)
    assert gate_passes(metrics), metrics


def test_exported_model_has_the_contract_shape() -> None:
    model = build_win_probability(Database())

    assert "available" in model
    if not model["available"]:
        return  # the gate failed: only the flag (and finite metrics) are published
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
    assert set(model["metrics"]) == METRIC_KEYS | {"fitGames"}
    assert len(model["teams"]) == 30
    assert all(len(tricode) == 3 for tricode in model["teams"])
