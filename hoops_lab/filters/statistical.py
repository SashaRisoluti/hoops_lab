"""Dynamic statistical filters: ``[field] [operator] [value]`` with AND/OR logic.

Comparison operators (``>``, ``<``, ``>=``, ``<=``, ``=``, ``!=``, ``between``)
become parameterized WHERE fragments; window operators (``top_n``,
``percentile_above``, ``percentile_below``) become QUALIFY fragments, which
DuckDB evaluates AFTER the WHERE clause — so percentiles and rankings always
refer to the already-filtered population, per the project's core rule.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

#: Plain SQL identifier (the injection guard for field/column names).
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

WHERE_OPS = frozenset({">", "<", ">=", "<=", "=", "!=", "between"})
WINDOW_OPS = frozenset({"top_n", "percentile_above", "percentile_below"})

Operator = Literal[
    ">",
    "<",
    ">=",
    "<=",
    "=",
    "!=",
    "between",
    "top_n",
    "percentile_above",
    "percentile_below",
]


def validate_identifier(name: str) -> str:
    """Return ``name`` if it is a plain SQL identifier, raise otherwise."""
    if not SAFE_IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return name


class StatFilter(BaseModel):
    """One ``[field] [operator] [value]`` condition."""

    field: str
    op: Operator
    value: float | list[float]

    @field_validator("field")
    @classmethod
    def _safe_field(cls, name: str) -> str:
        return validate_identifier(name)

    @model_validator(mode="after")
    def _check_value_shape(self) -> StatFilter:
        if self.op == "between":
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("'between' requires exactly two values")
        elif isinstance(self.value, list):
            raise ValueError(f"operator {self.op!r} takes a single numeric value")
        elif self.op == "top_n":
            if self.value < 1 or self.value != int(self.value):
                raise ValueError("'top_n' requires a positive integer")
        elif self.op in ("percentile_above", "percentile_below") and not 0 <= self.value <= 100:
            raise ValueError("percentile operators take a value between 0 and 100")
        return self

    def where_sql(self) -> tuple[str, list[float]]:
        """WHERE fragment + parameters (comparison operators only)."""
        if self.op not in WHERE_OPS:
            raise ValueError(f"{self.op!r} is a window operator — use qualify_sql()")
        if self.op == "between":
            low, high = self.value  # type: ignore[misc]
            return f'"{self.field}" BETWEEN ? AND ?', [float(low), float(high)]
        return f'"{self.field}" {self.op} ?', [float(self.value)]  # type: ignore[arg-type]

    def qualify_sql(self) -> tuple[str, list[float | int]]:
        """QUALIFY fragment + parameters (window operators only)."""
        if self.op == "top_n":
            return f'rank() OVER (ORDER BY "{self.field}" DESC) <= ?', [int(self.value)]  # type: ignore[arg-type]
        if self.op == "percentile_above":
            return f'percent_rank() OVER (ORDER BY "{self.field}") >= ?', [self.value / 100.0]  # type: ignore[operator]
        if self.op == "percentile_below":
            return f'percent_rank() OVER (ORDER BY "{self.field}") <= ?', [self.value / 100.0]  # type: ignore[operator]
        raise ValueError(f"{self.op!r} is a comparison operator — use where_sql()")


class StatFilterGroup(BaseModel):
    """A set of statistical filters combined with AND or OR logic.

    Window operators are restricted to AND groups: ORing a ranking condition
    with a row condition has no well-defined population semantics.
    """

    logic: Literal["AND", "OR"] = "AND"
    filters: list[StatFilter] = Field(min_length=1)

    @model_validator(mode="after")
    def _windows_need_and(self) -> StatFilterGroup:
        if self.logic == "OR" and any(f.op in WINDOW_OPS for f in self.filters):
            raise ValueError("window operators (top_n, percentile_*) require AND logic")
        return self

    def where_sql(self) -> tuple[str, list[float]]:
        """Combined WHERE fragment for the comparison filters ('' when none)."""
        fragments: list[str] = []
        params: list[float] = []
        for stat_filter in self.filters:
            if stat_filter.op in WHERE_OPS:
                fragment, values = stat_filter.where_sql()
                fragments.append(fragment)
                params.extend(values)
        if not fragments:
            return "", []
        return "(" + f" {self.logic} ".join(fragments) + ")", params

    def qualify_sql(self) -> list[tuple[str, list[float | int]]]:
        """QUALIFY fragments for the window filters (always combined with AND)."""
        return [f.qualify_sql() for f in self.filters if f.op in WINDOW_OPS]
