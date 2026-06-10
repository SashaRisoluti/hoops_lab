"""Contextual filters — MVP scope: game location (home/away).

Possession-level context (quarter, clutch time, garbage time, score margin,
transition vs half-court) requires the possession data built in Phase 4+;
this model grows with it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ContextualFilter(BaseModel):
    """Game-context constraints (game-grain tables only)."""

    location: Literal["home", "away"] | None = None

    @property
    def requires_game_grain(self) -> bool:
        """True when any contextual constraint is set."""
        return self.location is not None

    def where_parts(self) -> list[tuple[str, list]]:
        """WHERE fragments + parameters."""
        if self.location == "home":
            return [('"MATCHUP" LIKE ?', ["% vs. %"])]
        if self.location == "away":
            return [('"MATCHUP" LIKE ?', ["% @ %"])]
        return []
