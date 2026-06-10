"""Unit tests for NBAApiClient — no network access (remote calls are mocked)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from hoops_lab.ingestion.nba_api_client import NBAApiClient


def test_throttle_enforces_min_delay() -> None:
    client = NBAApiClient(delay=0.2)
    client._throttle()  # first call sets the reference timestamp
    start = time.monotonic()
    client._throttle()
    assert time.monotonic() - start >= 0.19


def test_league_player_stats_returns_first_dataframe() -> None:
    fake_endpoint = MagicMock()
    fake_endpoint.get_data_frames.return_value = [
        pd.DataFrame({"PLAYER_NAME": ["A"], "PTS": [30.5]})
    ]
    client = NBAApiClient(delay=0)
    with patch.object(client, "_call", return_value=fake_endpoint) as call:
        df = client.league_player_stats(season="2023-24")

    call.assert_called_once()
    assert list(df.columns) == ["PLAYER_NAME", "PTS"]
    assert len(df) == 1


def test_call_retries_then_raises_connection_error() -> None:
    failing_endpoint = MagicMock(side_effect=RuntimeError("boom"))
    failing_endpoint.__name__ = "FailingEndpoint"
    client = NBAApiClient(delay=0, max_retries=2)
    with patch("hoops_lab.ingestion.nba_api_client.time.sleep"):  # skip backoff waits
        with pytest.raises(ConnectionError, match="after 2 attempts"):
            client._call(failing_endpoint)
    assert failing_endpoint.call_count == 2


def test_team_id_from_name_resolves_reference_team() -> None:
    # Uses nba_api static data — works offline. Dallas Mavericks official id.
    assert NBAApiClient.team_id_from_name("Dallas Mavericks") == 1610612742


def test_team_id_from_name_rejects_unknown_team() -> None:
    with pytest.raises(ValueError, match="No NBA team matches"):
        NBAApiClient.team_id_from_name("Springfield Tigers")
