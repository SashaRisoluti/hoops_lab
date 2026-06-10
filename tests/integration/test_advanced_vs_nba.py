"""Validate computed advanced stats against nba_api's own values on the real DB.

Run pytest from the repo root; these tests are skipped automatically when the
local database has not been built yet (`python -m hoops_lab.storage.seed`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_ts_pct_calc_matches_endpoint_values() -> None:
    from hoops_lab.features.advanced import true_shooting_pct
    from hoops_lab.storage.database import Database

    db = Database(read_only=True)
    df = db.query_df(
        """
        SELECT b.PLAYER_ID, b.season, b.PTS, b.FGA, b.FTA, a.TS_PCT
        FROM player_season_stats AS b
        JOIN advanced_player_stats AS a
          ON a.PLAYER_ID = b.PLAYER_ID AND a.season = b.season
        WHERE b.MIN >= 25 AND b.GP >= 50
        """
    )
    db.close()

    assert len(df) > 100, "expected a meaningful sample of qualified players"

    out = true_shooting_pct(df)
    diff = (out["TS_PCT_CALC"] - out["TS_PCT"]).abs()

    # Per-game inputs are rounded to one decimal by the endpoint, so allow a
    # small tolerance; systematic formula errors would blow way past these.
    assert diff.median() < 0.005
    assert diff.max() < 0.02
