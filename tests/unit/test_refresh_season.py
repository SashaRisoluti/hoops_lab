"""The weekly refresh publishes exactly the refreshed season's raw files."""

from __future__ import annotations

from pathlib import Path

from scripts.refresh_season import publish_season


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
