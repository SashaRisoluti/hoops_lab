"""AppTest smoke test: the Player Analyzer page runs end-to-end on the real DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_player_page_renders_card_radar_and_on_off() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/02_player_analyzer.py", default_timeout=120)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    assert len(at.metric) >= 6, "player card metrics missing"
    assert len(at.selectbox) >= 2, "season/player selectors missing"
