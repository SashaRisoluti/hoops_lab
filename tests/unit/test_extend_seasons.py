"""The whole-season PBP sample: complete seasons only, union with the published sample."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from hoops_lab.ingestion.historical import HistoricalDownloader
from scripts.extend_seasons import extend_pbp_sample


def _team_box(games: int) -> pd.DataFrame:
    ids = [f"00221{i:05d}" for i in range(1, games + 1)]
    return pd.DataFrame({"GAME_ID": ids + ids})


def test_refuses_an_incomplete_season(tmp_path) -> None:
    _team_box(400).to_parquet(tmp_path / "team_box_2026-27.parquet", index=False)
    client = MagicMock()
    downloader = HistoricalDownloader(client=client, raw_dir=tmp_path / "raw")

    with pytest.raises(SystemExit, match="not complete"):
        extend_pbp_sample(downloader, "2026-27", n=10, seed=0, processed_dir=tmp_path)
    client.fetch_df.assert_not_called()


def test_unions_random_games_with_the_published_sample(tmp_path) -> None:
    _team_box(1230).to_parquet(tmp_path / "team_box_2021-22.parquet", index=False)
    published = pd.DataFrame({"gameId": ["0022101230"], "actionNumber": [1]})
    published.to_parquet(tmp_path / "play_by_play_sample_2021-22.parquet", index=False)
    client = MagicMock()
    client.fetch_df.side_effect = lambda _endpoint, game_id: pd.DataFrame(
        {"gameId": [game_id], "actionNumber": [1]}
    )
    downloader = HistoricalDownloader(client=client, raw_dir=tmp_path / "raw")

    result = extend_pbp_sample(downloader, "2021-22", n=5, seed=0, processed_dir=tmp_path)

    saved = pd.read_parquet(result.path)
    assert "0022101230" in set(saved["gameId"])  # published games are kept
    assert saved["gameId"].nunique() in (5, 6)  # 5 random games, one may already be published
    assert result.path.parent == tmp_path / "raw"  # staged, never written into data/processed
