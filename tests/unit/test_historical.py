"""Unit tests for HistoricalDownloader — nba_api calls are mocked (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from hoops_lab.ingestion.historical import (
    LEAGUE_DATASETS,
    HistoricalDownloader,
    recent_team_game_ids,
)


def make_client(df: pd.DataFrame) -> MagicMock:
    client = MagicMock()
    client.fetch_df.return_value = df
    return client


def test_download_dataset_saves_parquet_and_reports_rows(tmp_path) -> None:
    df = pd.DataFrame({"PLAYER_ID": [1, 2], "PTS": [10.0, 20.0]})
    downloader = HistoricalDownloader(client=make_client(df), raw_dir=tmp_path)

    result = downloader.download_dataset("player_box", season="2023-24")

    assert result.dataset == "player_box"
    assert result.season == "2023-24"
    assert result.rows == 2
    assert result.path == tmp_path / "player_box_2023-24.parquet"
    saved = pd.read_parquet(result.path)
    assert len(saved) == 2


def test_download_dataset_rejects_unknown_dataset(tmp_path) -> None:
    downloader = HistoricalDownloader(client=make_client(pd.DataFrame()), raw_dir=tmp_path)
    with pytest.raises(KeyError, match="unknown_thing"):
        downloader.download_dataset("unknown_thing", season="2023-24")


def test_download_season_bundle_covers_all_league_datasets(tmp_path) -> None:
    df = pd.DataFrame({"A": [1]})
    client = make_client(df)
    downloader = HistoricalDownloader(client=client, raw_dir=tmp_path)

    results = downloader.download_season_bundle("2023-24")

    assert {r.dataset for r in results} == set(LEAGUE_DATASETS)
    assert client.fetch_df.call_count == len(LEAGUE_DATASETS)
    for r in results:
        assert r.path.exists()


def test_download_play_by_play_merges_games(tmp_path) -> None:
    client = MagicMock()
    client.fetch_df.side_effect = [
        pd.DataFrame({"gameId": ["001"], "actionNumber": [1]}),
        pd.DataFrame({"gameId": ["002"], "actionNumber": [1]}),
    ]
    downloader = HistoricalDownloader(client=client, raw_dir=tmp_path)

    result = downloader.download_play_by_play(["001", "002"], season="2023-24")

    assert result.rows == 2
    saved = pd.read_parquet(result.path)
    assert sorted(saved["gameId"]) == ["001", "002"]


def test_download_shot_chart_passes_team_id(tmp_path) -> None:
    df = pd.DataFrame({"LOC_X": [0], "LOC_Y": [0]})
    client = make_client(df)
    downloader = HistoricalDownloader(client=client, raw_dir=tmp_path)

    result = downloader.download_shot_chart(season="2023-24", team_id=1610612742)

    assert result.dataset == "shot_chart"
    assert client.fetch_df.call_args.kwargs.get("team_id") == 1610612742


def test_recent_team_game_ids_filters_sorts_and_limits() -> None:
    team_box = pd.DataFrame(
        {
            "TEAM_ID": [1, 1, 2, 1],
            "GAME_ID": ["003", "004", "002", "001"],
            "GAME_DATE": ["2024-04-08", "2024-04-10", "2024-04-08", "2024-04-05"],
        }
    )
    assert recent_team_game_ids(team_box, team_id=1, n=2) == ["004", "003"]
