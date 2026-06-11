"""AppTest smoke tests: the four Phase 3 pages run end-to-end on the real DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def _run(page: str, timeout: int = 120):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(f"dashboard/pages/{page}", default_timeout=timeout)
    at.run()
    assert not at.exception, f"{page} raised: {at.exception}"
    return at


def test_team_identity_page() -> None:
    at = _run("03_team_identity.py")
    assert len(at.metric) >= 4, "ratings metrics missing"


def test_opponent_scouting_page() -> None:
    # Longer timeout: the Shot Archetypes section profiles ~220k league shots
    # and fits KMeans + SOM on the first (uncached) run.
    at = _run("04_opponent_scouting.py", timeout=300)
    assert len(at.dataframe) >= 2, "top players / lineups tables missing"
    # Shot Archetypes section: controls + archetype/closest-players tables.
    assert len(at.slider) >= 2, "min_attempts / n_clusters sliders missing"
    assert len(at.dataframe) >= 4, "archetype summary / closest players tables missing"
    assert len(at.metric) >= 6, "data summary metrics missing"


def test_matchup_page() -> None:
    at = _run("05_matchup_analysis.py")
    assert len(at.dataframe) >= 1, "matchup table missing"


def test_shot_map_page() -> None:
    at = _run("06_shot_map.py")
    assert len(at.dataframe) >= 1, "zone efficiency table missing"
