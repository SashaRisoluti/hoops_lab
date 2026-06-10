"""Pydantic models validating ingestion inputs and outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

#: Season types accepted by stats.nba.com endpoints.
SeasonType = Literal["Regular Season", "Playoffs", "Pre Season"]

_SEASON_RE = re.compile(r"\d{4}-\d{2}")


class HistoricalDownloadRequest(BaseModel):
    """Validated request for a historical download run.

    Attributes
    ----------
    seasons:
        Seasons in NBA format (e.g. ``"2023-24"``); at least one.
    season_type:
        Which part of the season to download.
    """

    seasons: list[str] = Field(min_length=1)
    season_type: SeasonType = "Regular Season"

    @field_validator("seasons")
    @classmethod
    def _validate_season_format(cls, seasons: list[str]) -> list[str]:
        for season in seasons:
            if not _SEASON_RE.fullmatch(season):
                raise ValueError(f"season {season!r} must match YYYY-YY, e.g. '2023-24'")
            start_year = int(season[:4])
            suffix = int(season[5:])
            if (start_year + 1) % 100 != suffix:
                raise ValueError(f"season {season!r} years must be consecutive, e.g. '2023-24'")
        return seasons


class DownloadResult(BaseModel):
    """Metadata about one raw dataset saved to disk."""

    dataset: str
    season: str
    rows: int = Field(ge=0)
    path: Path
