"""The weekly refresh publishes exactly the refreshed season and pushes safely."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import refresh_season
from scripts.refresh_season import PUBLISHED_PATHS, publish_season


def test_publish_copies_only_the_refreshed_season(tmp_path: Path) -> None:
    raw, processed = tmp_path / "raw", tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    for name in (
        "team_box_2026-27.parquet",
        "shot_chart_1610612737_2026-27.parquet",
        "team_box_2025-26.parquet",
    ):
        (raw / name).write_bytes(b"fresh")
    (processed / "team_box_2026-27.parquet").write_bytes(b"stale")

    copied = publish_season("2026-27", raw, processed)

    assert sorted(path.name for path in copied) == [
        "shot_chart_1610612737_2026-27.parquet",
        "team_box_2026-27.parquet",
    ]
    assert (processed / "team_box_2026-27.parquet").read_bytes() == b"fresh"
    assert not (processed / "team_box_2025-26.parquet").exists()


def _offline(monkeypatch: pytest.MonkeyPatch, branch: str = "main") -> list[tuple[str, ...]]:
    """Record git calls instead of running them and skip the download; data always changed."""
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        changed = int(args[0] == "diff")  # `diff --quiet` exits 1 when something is staged
        return subprocess.CompletedProcess(args, changed, stdout=f"{branch}\n", stderr="")

    monkeypatch.setattr(refresh_season, "_git", fake_git)
    monkeypatch.setattr(refresh_season, "refresh", lambda season, skip_pbp: None)
    monkeypatch.chdir(refresh_season.ROOT)  # main() chdirs there; restored after the test
    return calls


def test_push_off_main_refuses_before_downloading(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _offline(monkeypatch, branch="feature/x")
    monkeypatch.setattr(refresh_season, "refresh", lambda *_: pytest.fail("downloaded off main"))

    assert refresh_season.main(["--push"]) == 1
    assert calls == [("branch", "--show-current")]


def test_push_commits_only_published_paths_on_latest_main(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _offline(monkeypatch)
    monkeypatch.setattr(refresh_season, "_gate_passes", lambda: True)

    assert refresh_season.main(["--push"]) == 0
    assert [call[0] for call in calls] == [
        "branch",
        "pull",
        "add",
        "diff",
        "commit",
        "pull",
        "push",
    ]
    diff, commit = calls[3], calls[4]
    assert diff[-3:] == commit[-3:] == ("--", *PUBLISHED_PATHS)


def test_failing_gate_never_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _offline(monkeypatch)
    monkeypatch.setattr(refresh_season, "_gate_passes", lambda: False)

    assert refresh_season.main(["--push"]) == 1
    assert [call[0] for call in calls] == ["branch", "pull"]
