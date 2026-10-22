"""LivePoller: one throttle clock per feed, live CDN first, stats.nba.com fallback."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

import hoops_lab.live.poller as poller_module
from hoops_lab.live.poller import LIVE_FEED, STATS_FALLBACK, LivePoller


def _blocked(*args: object) -> None:
    raise ValueError("Expecting value: line 1 column 1 (char 0)")  # what a CDN 403 looks like


@pytest.fixture
def fake_feed(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, int], list[float]]:
    """Stub every fetcher and the clock; return (call counts, clock)."""
    calls = {"scoreboard": 0, "pbp": 0, "stats_scoreboard": 0, "stats_pbp": 0}
    now = [100.0]

    def scoreboard() -> list[dict]:
        calls["scoreboard"] += 1
        return []

    def play_by_play(game_id: str) -> list[dict]:
        calls["pbp"] += 1
        return []

    def stats_scoreboard(client: object, game_date: object) -> list[dict]:
        calls["stats_scoreboard"] += 1
        return [{"gameId": "g1"}]

    def stats_play_by_play(client: object, game_id: str) -> pd.DataFrame:
        calls["stats_pbp"] += 1
        return pd.DataFrame()

    monkeypatch.setattr(poller_module, "fetch_live_scoreboard", scoreboard)
    monkeypatch.setattr(poller_module, "fetch_live_play_by_play", play_by_play)
    monkeypatch.setattr(poller_module, "fetch_stats_scoreboard", stats_scoreboard)
    monkeypatch.setattr(poller_module, "fetch_stats_play_by_play", stats_play_by_play)
    monkeypatch.setattr(poller_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return calls, now


def test_play_by_play_refreshes_on_every_poll_after_the_scoreboard(fake_feed) -> None:
    calls, now = fake_feed
    poller = LivePoller(min_interval=2.0)

    for _ in range(5):  # one page rerun = scoreboard, then the chosen game's events
        poller.scoreboard()
        poller.events("g1")
        now[0] += 3.0

    assert (calls["scoreboard"], calls["pbp"]) == (5, 5)


def test_calls_inside_the_interval_are_served_from_cache(fake_feed) -> None:
    calls, now = fake_feed
    poller = LivePoller(min_interval=2.0)

    for _ in range(3):
        poller.scoreboard()
        poller.events("g1")
        now[0] += 0.5

    assert (calls["scoreboard"], calls["pbp"]) == (1, 1)


def test_each_game_has_its_own_clock(fake_feed) -> None:
    calls, _ = fake_feed
    poller = LivePoller(min_interval=2.0)

    poller.events("g1")
    poller.events("g2")

    assert calls["pbp"] == 2


def test_live_feed_is_used_when_it_answers(fake_feed) -> None:
    calls, _ = fake_feed
    poller = LivePoller(min_interval=2.0)

    assert poller.scoreboard() == []
    assert poller.source == LIVE_FEED
    assert poller.updated_at is not None
    assert calls["stats_scoreboard"] == 0


def test_scoreboard_falls_back_to_stats_when_the_live_feed_fails(fake_feed, monkeypatch) -> None:
    calls, _ = fake_feed
    monkeypatch.setattr(poller_module, "fetch_live_scoreboard", _blocked)
    poller = LivePoller(min_interval=2.0)

    assert poller.source is None
    assert poller.scoreboard() == [{"gameId": "g1"}]
    assert poller.source == STATS_FALLBACK
    assert calls["stats_scoreboard"] == 1


def test_live_actions_are_adapted_to_the_stats_contract(fake_feed, monkeypatch) -> None:
    action = {
        "actionNumber": 2,
        "period": 1,
        "clock": "PT11M30.00S",
        "teamId": 10,
        "actionType": "3pt",
        "shotResult": "Made",
    }
    monkeypatch.setattr(poller_module, "fetch_live_play_by_play", lambda game_id: [action])

    events = LivePoller(min_interval=2.0).events("g1")

    assert events["actionType"].tolist() == ["Made Shot"]
    assert events["shotValue"].tolist() == [3]
    assert (events["gameId"] == "g1").all()


def test_stats_play_by_play_is_used_as_is_in_chronological_order(fake_feed, monkeypatch) -> None:
    pbp = pd.DataFrame(
        {
            "gameId": ["g1"] * 3,
            "actionNumber": [1, 3, 2],  # a late-inserted row, as raw PBPv3 feeds have
            "period": [1, 1, 1],
            "clock": ["PT12M00.00S", "PT10M00.00S", "PT11M00.00S"],
            "actionType": ["period", "Made Shot", "Missed Shot"],
        }
    )
    monkeypatch.setattr(poller_module, "fetch_live_play_by_play", _blocked)
    monkeypatch.setattr(poller_module, "fetch_stats_play_by_play", lambda client, game_id: pbp)
    poller = LivePoller(min_interval=2.0)

    events = poller.events("g1")

    assert list(events.columns) == list(pbp.columns)
    assert events["actionNumber"].tolist() == [1, 2, 3]
    assert poller.source == STATS_FALLBACK


def test_both_sources_failing_raises_connection_error(fake_feed, monkeypatch) -> None:
    monkeypatch.setattr(poller_module, "fetch_live_scoreboard", _blocked)
    monkeypatch.setattr(poller_module, "fetch_stats_scoreboard", _blocked)

    with pytest.raises(ConnectionError, match="both unavailable"):
        LivePoller(min_interval=2.0).scoreboard()
