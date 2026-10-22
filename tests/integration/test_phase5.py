"""Phase 5 integration: the Live Command Center page in replay mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH, ENVIRONMENT

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_live_command_center_replay_renders() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/08_live_command_center.py", default_timeout=120)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    # Live KPI strip renders StatTile HTML via st.markdown, not st.metric.
    strip_html = "".join(m.value for m in at.markdown)
    assert "eFG%" in strip_html, "live KPI strip missing"
    assert "PPP" in strip_html, "live KPI strip missing"
    assert len(at.dataframe) >= 1, "timeline / comparison tables missing"


@pytest.mark.skipif(ENVIRONMENT == "production", reason="live mode is disabled in production")
def test_live_mode_renders_through_the_stats_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live CDN blocked -> stats fallback -> same pipeline; no network (fetchers stubbed)."""
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    import hoops_lab.live.poller as poller_module

    pbp_file = sorted(Path("data/processed").glob("play_by_play_sample_*.parquet"))[-1]
    pbp = pd.read_parquet(pbp_file)
    game = pbp.loc[pbp["gameId"] == pbp["gameId"].iloc[0]]
    teams = game.loc[game["teamId"] > 0].drop_duplicates("location").set_index("location")
    scoreboard_game = {
        "gameId": game["gameId"].iloc[0],
        "gameStatus": 3,
        "gameStatusText": "Final",
        "homeTeam": {
            "teamId": teams.at["h", "teamId"],
            "teamTricode": teams.at["h", "teamTricode"],
        },
        "awayTeam": {
            "teamId": teams.at["v", "teamId"],
            "teamTricode": teams.at["v", "teamTricode"],
        },
    }

    def blocked(*args: object) -> None:
        raise ValueError("Expecting value: line 1 column 1 (char 0)")

    monkeypatch.setattr(poller_module, "fetch_live_scoreboard", blocked)
    monkeypatch.setattr(poller_module, "fetch_live_play_by_play", blocked)
    monkeypatch.setattr(poller_module, "fetch_stats_scoreboard", lambda c, d: [scoreboard_game])
    monkeypatch.setattr(poller_module, "fetch_stats_play_by_play", lambda c, g: game)

    at = AppTest.from_file("dashboard/pages/08_live_command_center.py", default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value("Live (nba_api)").run()

    assert not at.exception, f"page raised: {at.exception}"
    strip_html = "".join(m.value for m in at.markdown)
    assert "PPP" in strip_html, "live KPI strip missing"
    captions = " ".join(c.value for c in at.caption)
    assert "stats.nba.com fallback" in captions, "data source caption missing"
