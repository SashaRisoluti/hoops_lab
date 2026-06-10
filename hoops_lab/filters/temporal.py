"""Temporal filters: seasons, date ranges, last N games.

Season filters work on every base table; date ranges and ``last_n_games``
need game-grain tables (the query builder validates this).
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

_SEASON_RE = re.compile(r"\d{4}-\d{2}")


class TemporalFilter(BaseModel):
    """Season / date / recency constraints."""

    seasons: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    last_n_games: int | None = Field(default=None, ge=1)

    @field_validator("seasons")
    @classmethod
    def _season_format(cls, seasons: list[str] | None) -> list[str] | None:
        for season in seasons or []:
            if not _SEASON_RE.fullmatch(season):
                raise ValueError(f"season {season!r} must match YYYY-YY, e.g. '2023-24'")
        return seasons

    @property
    def requires_game_grain(self) -> bool:
        """True when the filter only makes sense on per-game rows."""
        return bool(self.last_n_games or self.date_from or self.date_to)

    def where_parts(self) -> list[tuple[str, list]]:
        """WHERE fragments + parameters (everything except last_n_games)."""
        parts: list[tuple[str, list]] = []
        if self.seasons:
            placeholders = ", ".join("?" for _ in self.seasons)
            parts.append((f"season IN ({placeholders})", list(self.seasons)))
        if self.date_from:
            parts.append(('CAST("GAME_DATE" AS DATE) >= ?', [str(self.date_from)]))
        if self.date_to:
            parts.append(('CAST("GAME_DATE" AS DATE) <= ?', [str(self.date_to)]))
        return parts

    def qualify_part(self, partition_col: str) -> tuple[str, list] | None:
        """QUALIFY fragment keeping each entity's most recent N games."""
        if not self.last_n_games:
            return None
        fragment = (
            f'row_number() OVER (PARTITION BY "{partition_col}" ORDER BY "GAME_DATE" DESC) <= ?'
        )
        return fragment, [self.last_n_games]
