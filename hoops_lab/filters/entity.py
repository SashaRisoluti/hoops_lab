"""Entity filters: teams, players and minimum-sample thresholds.

Minimum-sample thresholds (minutes, games) implement the project rule that
every analysis must guard against small samples.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityFilter(BaseModel):
    """Team/player selection and minimum-sample constraints."""

    team_ids: list[int] | None = None
    player_ids: list[int] | None = None
    min_minutes: float | None = Field(default=None, ge=0)
    min_games: int | None = Field(default=None, ge=0)

    def where_parts(self) -> list[tuple[str, list]]:
        """WHERE fragments + parameters."""
        parts: list[tuple[str, list]] = []
        if self.team_ids:
            placeholders = ", ".join("?" for _ in self.team_ids)
            parts.append((f'"TEAM_ID" IN ({placeholders})', list(self.team_ids)))
        if self.player_ids:
            placeholders = ", ".join("?" for _ in self.player_ids)
            parts.append((f'"PLAYER_ID" IN ({placeholders})', list(self.player_ids)))
        if self.min_minutes is not None:
            parts.append(('"MIN" >= ?', [self.min_minutes]))
        if self.min_games is not None:
            parts.append(('"GP" >= ?', [self.min_games]))
        return parts
