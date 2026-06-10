"""Phase 6 integration: model quality gates on real data + the report page."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_shot_quality_beats_baseline_on_holdout_season() -> None:
    """Temporal split: train on 2023-25, evaluate log-loss on 2025-26."""
    import numpy as np
    from sklearn.metrics import log_loss

    from hoops_lab.models.shot_quality_model import score_shots, temporal_split, train_shot_quality
    from hoops_lab.storage.database import Database

    db = Database()
    shots = db.query_df("SELECT * FROM shots")
    train, test = temporal_split(shots, test_season="2025-26")
    assert len(train) > 10_000 and len(test) > 5_000

    model = train_shot_quality(train)
    scored = score_shots(model, test)

    model_loss = log_loss(test["SHOT_MADE_FLAG"], scored["XFG"])
    baseline_loss = log_loss(
        test["SHOT_MADE_FLAG"], np.full(len(test), train["SHOT_MADE_FLAG"].mean())
    )
    assert model_loss < baseline_loss - 0.01, (
        f"model log-loss {model_loss:.4f} must beat the {baseline_loss:.4f} baseline"
    )


def test_win_probability_separates_outcomes_on_holdout_games() -> None:
    from sklearn.metrics import roc_auc_score

    from hoops_lab.models.win_probability import build_states_from_db, train_win_probability
    from hoops_lab.storage.database import Database

    db = Database()
    states = build_states_from_db(db)
    games = sorted(states["game_id"].unique())
    assert len(games) >= 20

    train = states.loc[states["game_id"].isin(games[:16])]
    test = states.loc[states["game_id"].isin(games[16:])]
    model = train_win_probability(train)

    from hoops_lab.models.win_probability import predict_wp_frame

    auc = roc_auc_score(test["home_won"], predict_wp_frame(model, test))
    assert auc > 0.75, f"in-game WP AUC {auc:.3f} too low"


def test_post_game_review_page_renders() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/09_post_game_review.py", default_timeout=180)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    assert len(at.dataframe) >= 2, "four factors / top players tables missing"
