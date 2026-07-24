"""Consistent page header (design spec 2026-07-24, section 2).

Pure render: builder returns HTML, wrapper draws it and returns None.
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.theme import (
    BG_TILE,
    BORDER,
    FONT_DISPLAY,
    FONT_MONO,
    TEXT,
    TEXT_MUTED,
    TEXT_SOFT,
)


def page_header_html(
    title: str,
    subtitle: str | None = None,
    context_chips: list[str] | None = None,
) -> str:
    """Build the page header block.

    Args:
        title: Page title (Inter Tight display).
        subtitle: Optional muted line under the title.
        context_chips: Optional small mono pills on the right (season, team...).

    Returns:
        HTML string for the header block.
    """
    subtitle_html = (
        f'<div style="font-size:13px;color:{TEXT_MUTED};">{subtitle}</div>' if subtitle else ""
    )
    chips_html = ""
    if context_chips:
        chips = "".join(
            f'<span style="font-family:{FONT_MONO};font-size:10px;letter-spacing:0.08em;'
            f"color:{TEXT_SOFT};background:{BG_TILE};border:1px solid {BORDER};"
            f'border-radius:999px;padding:3px 10px;">{chip}</span>'
            for chip in context_chips
        )
        chips_html = f'<div style="display:flex;gap:6px;">{chips}</div>'
    return (
        '<div style="display:flex;align-items:flex-end;justify-content:space-between;'
        'margin:2px 0 14px;">'
        f'<div><div style="font-family:{FONT_DISPLAY};font-size:26px;font-weight:800;'
        f'letter-spacing:-0.01em;color:{TEXT};">{title}</div>{subtitle_html}</div>'
        f"{chips_html}</div>"
    )


def render_page_header(
    title: str,
    subtitle: str | None = None,
    context_chips: list[str] | None = None,
) -> None:
    """Draw the page header into the current Streamlit container."""
    st.markdown(page_header_html(title, subtitle, context_chips), unsafe_allow_html=True)
