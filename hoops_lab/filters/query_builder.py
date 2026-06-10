"""Builds dynamic, parameterized DuckDB SQL from validated filter models.

Injection guard has three layers: base tables come from a fixed registry,
every identifier (columns, fields, order_by) is regex-validated and
double-quoted, and every value travels as a ``?`` parameter.

Window-based conditions (top_n, percentile_*, last_n_games) are emitted as
QUALIFY clauses: DuckDB evaluates them after WHERE, so rankings and
percentiles always refer to the filtered population.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

from hoops_lab.filters.contextual import ContextualFilter
from hoops_lab.filters.entity import EntityFilter
from hoops_lab.filters.statistical import StatFilterGroup, validate_identifier
from hoops_lab.filters.temporal import TemporalFilter
from hoops_lab.storage.database import Database


@dataclass(frozen=True)
class BaseTable:
    """A queryable base table and its capabilities."""

    table: str
    game_grain: bool = False
    lastn_partition: str | None = None


#: Whitelisted base tables exposed to the filter engine.
BASE_TABLES: dict[str, BaseTable] = {
    "player_season_full": BaseTable("player_season_full"),
    "player_season": BaseTable("player_season_stats"),
    "player_advanced": BaseTable("advanced_player_stats"),
    "team_season": BaseTable("team_season_stats"),
    "team_advanced": BaseTable("advanced_team_stats"),
    "player_game": BaseTable("box_scores_player", game_grain=True, lastn_partition="PLAYER_ID"),
    "team_game": BaseTable("box_scores_team", game_grain=True, lastn_partition="TEAM_ID"),
}

BaseName = Literal[
    "player_season_full",
    "player_season",
    "player_advanced",
    "team_season",
    "team_advanced",
    "player_game",
    "team_game",
]


class QueryRequest(BaseModel):
    """A complete, validated query specification."""

    base: BaseName
    columns: list[str] | None = None
    temporal: TemporalFilter = Field(default_factory=TemporalFilter)
    entity: EntityFilter = Field(default_factory=EntityFilter)
    contextual: ContextualFilter = Field(default_factory=ContextualFilter)
    stats: StatFilterGroup | None = None
    order_by: str | None = None
    descending: bool = True
    limit: int | None = Field(default=None, ge=1)

    @field_validator("columns")
    @classmethod
    def _safe_columns(cls, columns: list[str] | None) -> list[str] | None:
        for column in columns or []:
            validate_identifier(column)
        return columns

    @field_validator("order_by")
    @classmethod
    def _safe_order_by(cls, order_by: str | None) -> str | None:
        if order_by is not None:
            validate_identifier(order_by)
        return order_by

    @model_validator(mode="after")
    def _grain_compatibility(self) -> QueryRequest:
        spec = BASE_TABLES[self.base]
        if not spec.game_grain and (
            self.temporal.requires_game_grain or self.contextual.requires_game_grain
        ):
            raise ValueError(
                "date ranges, last_n_games and contextual filters require a "
                "game-grain base table (player_game or team_game)"
            )
        return self


def build_query(request: QueryRequest) -> tuple[str, list]:
    """Translate a :class:`QueryRequest` into ``(sql, parameters)``."""
    spec = BASE_TABLES[request.base]

    select = ", ".join(f'"{c}"' for c in request.columns) if request.columns else "*"

    where_parts: list[tuple[str, list]] = []
    where_parts.extend(request.temporal.where_parts())
    where_parts.extend(request.entity.where_parts())
    where_parts.extend(request.contextual.where_parts())
    if request.stats:
        fragment, params = request.stats.where_sql()
        if fragment:
            where_parts.append((fragment, params))

    qualify_parts: list[tuple[str, list]] = []
    if request.stats:
        qualify_parts.extend(request.stats.qualify_sql())
    if spec.lastn_partition:
        last_n = request.temporal.qualify_part(spec.lastn_partition)
        if last_n:
            qualify_parts.append(last_n)

    sql = f'SELECT {select} FROM "{spec.table}"'
    parameters: list = []

    if where_parts:
        sql += " WHERE " + " AND ".join(fragment for fragment, _ in where_parts)
        for _, params in where_parts:
            parameters.extend(params)

    if qualify_parts:
        sql += " QUALIFY " + " AND ".join(fragment for fragment, _ in qualify_parts)
        for _, params in qualify_parts:
            parameters.extend(params)

    if request.order_by:
        sql += f' ORDER BY "{request.order_by}" {"DESC" if request.descending else "ASC"}'

    if request.limit is not None:
        sql += " LIMIT ?"
        parameters.append(request.limit)

    return sql, parameters


def run_query(db: Database, request: QueryRequest) -> pd.DataFrame:
    """Build and execute a query, returning the result as a DataFrame."""
    sql, parameters = build_query(request)
    return db.query_df(sql, parameters)
