"""Standardized searchable entity picker (design spec 2026-07-24, section 2).

Wraps st.selectbox (which ships type-to-search) so every page gets the
same picker UX and label formatting. Input widgets return the selection —
same contract as team_rail.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

import streamlit as st

T = TypeVar("T")


def entity_label(name: str, meta: str | None = None) -> str:
    """'Name · meta' display label; plain name when meta is missing."""
    return f"{name} · {meta}" if meta else name


def search_select(
    label: str,
    options: Sequence[T],
    format_func: Callable[[T], str] = str,
    key: str | None = None,
    index: int | None = 0,
    help_text: str | None = None,
) -> T | None:
    """Searchable selectbox with the shared picker semantics.

    Args:
        label: Widget label.
        options: Selectable values (ids or plain strings).
        format_func: Maps an option to its display label (use entity_label).
        key: Session-state key (pages prefix with their page name).
        index: Default selected index; None starts empty and shows the
            placeholder.
        help_text: Optional help tooltip.

    Returns:
        The selected option, or None when index=None and nothing is
        chosen yet.
    """
    return st.selectbox(
        label,
        options,
        index=index,
        format_func=format_func,
        key=key,
        help=help_text,
        placeholder="Search…",
    )
