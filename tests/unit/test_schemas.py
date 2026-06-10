"""Unit tests for ingestion schemas (Pydantic validation)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hoops_lab.ingestion.schemas import DownloadResult, HistoricalDownloadRequest


def test_accepts_valid_seasons() -> None:
    req = HistoricalDownloadRequest(seasons=["2023-24", "2025-26"])
    assert req.seasons == ["2023-24", "2025-26"]
    assert req.season_type == "Regular Season"


def test_rejects_malformed_season_string() -> None:
    with pytest.raises(ValidationError, match="season"):
        HistoricalDownloadRequest(seasons=["2023-2024"])


def test_rejects_inconsistent_season_years() -> None:
    # The two-digit suffix must be the start year + 1.
    with pytest.raises(ValidationError, match="consecutive"):
        HistoricalDownloadRequest(seasons=["2023-26"])


def test_rejects_unknown_season_type() -> None:
    with pytest.raises(ValidationError):
        HistoricalDownloadRequest(seasons=["2023-24"], season_type="Summer League")


def test_rejects_empty_seasons_list() -> None:
    with pytest.raises(ValidationError):
        HistoricalDownloadRequest(seasons=[])


def test_download_result_rejects_negative_rows() -> None:
    with pytest.raises(ValidationError):
        DownloadResult(dataset="player_box", season="2023-24", rows=-1, path="x.parquet")
