"""LivePoller throttles each live endpoint on its own clock."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import hoops_lab.live.poller as poller_module
from hoops_lab.live.poller import LivePoller


@pytest.fixture
def fake_feed(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, int], list[float]]:
    """Stub both live fetchers and the clock; return (call counts, clock)."""
    calls = {"scoreboard": 0, "pbp": 0}
    now = [100.0]

    def scoreboard() -> list[dict]:
        calls["scoreboard"] += 1
        return []

    def play_by_play(game_id: str) -> list[dict]:
        calls["pbp"] += 1
        return []

    monkeypatch.setattr(poller_module, "fetch_live_scoreboard", scoreboard)
    monkeypatch.setattr(poller_module, "fetch_live_play_by_play", play_by_play)
    monkeypatch.setattr(poller_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return calls, now


def test_play_by_play_refreshes_on_every_poll_after_the_scoreboard(fake_feed) -> None:
    calls, now = fake_feed
    poller = LivePoller(min_interval=2.0)

    for _ in range(5):  # one page rerun = scoreboard, then the chosen game's PBP
        poller.scoreboard()
        poller.play_by_play("g1")
        now[0] += 3.0

    assert calls == {"scoreboard": 5, "pbp": 5}


def test_calls_inside_the_interval_are_served_from_cache(fake_feed) -> None:
    calls, now = fake_feed
    poller = LivePoller(min_interval=2.0)

    for _ in range(3):
        poller.scoreboard()
        poller.play_by_play("g1")
        now[0] += 0.5

    assert calls == {"scoreboard": 1, "pbp": 1}


def test_each_game_has_its_own_clock(fake_feed) -> None:
    calls, _ = fake_feed
    poller = LivePoller(min_interval=2.0)

    poller.play_by_play("g1")
    poller.play_by_play("g2")

    assert calls["pbp"] == 2
