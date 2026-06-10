"""Phase 4 integration: possession invariant on real PBP + Lineup Explorer page."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_possession_points_match_final_scores() -> None:
    """Score-delta accounting must reproduce each game's final score.

    Tolerance covers technical free throws made by the defending team,
    which the parser deliberately does not attribute (documented limit).
    """
    from hoops_lab.features.possession import build_possessions
    from hoops_lab.storage.database import Database

    # Same (write-mode) configuration as the cached dashboard connection:
    # DuckDB forbids mixed read-only/read-write opens within one process.
    db = Database()
    pbp = db.query_df("SELECT * FROM play_by_play")
    finals = db.query_df(
        "SELECT GAME_ID, TEAM_ID, PTS FROM box_scores_team "
        "WHERE GAME_ID IN (SELECT DISTINCT gameId FROM play_by_play)"
    )
    db.close()

    possessions = build_possessions(pbp)
    scored = possessions.groupby(["game_id", "offense_team_id"])["points"].sum().reset_index()
    merged = scored.merge(
        finals, left_on=["game_id", "offense_team_id"], right_on=["GAME_ID", "TEAM_ID"]
    )

    assert len(merged) == len(finals), "every game-team must be reconstructed"
    diff = (merged["points"] - merged["PTS"]).abs()
    assert diff.median() == 0, "score accounting must be exact for most games"
    assert diff.max() <= 6, f"max per-team deviation too large: {diff.max()}"

    # Sanity: NBA teams average roughly 95-110 possessions per game.
    per_game = possessions.groupby(["game_id", "offense_team_id"]).size()
    assert 85 <= per_game.median() <= 115


def test_lineup_explorer_page_renders() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/07_lineup_explorer.py", default_timeout=120)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    assert len(at.dataframe) >= 1, "lineup table missing"
