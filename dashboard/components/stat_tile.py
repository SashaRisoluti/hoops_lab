"""Worldcup26-style stat tiles (design spec 2026-07-24, section 2).

Pure render helpers: the builder returns an HTML string, the render
wrapper draws tiles into Streamlit columns and returns None. No database
access — data arrives already formatted.
"""

from __future__ import annotations

import math

import streamlit as st

from dashboard.components.theme import (
    BG_TILE,
    BORDER,
    COLOR_GOOD,
    COLOR_WEAK_SOFT,
    FONT_DISPLAY,
    FONT_MONO,
    TEXT,
    TEXT_MUTED,
    pctl_color,
    pctl_text_color,
)

_EYEBROW = f"font-family:{FONT_MONO};font-size:10px;letter-spacing:0.12em;color:{TEXT_MUTED};"


def _display_value(value: str | float | None) -> str:
    """Missing data renders as an em-dash (spec section 5)."""
    if value is None:
        return "—"
    if isinstance(value, float) and math.isnan(value):
        return "—"
    return str(value)


def stat_tile_html(
    label: str,
    value: str | float | None,
    sub: str | None = None,
    delta: float | None = None,
    pctl: float | None = None,
) -> str:
    """Build one stat tile.

    Args:
        label: Uppercase eyebrow label.
        value: Main value, pre-formatted; None/NaN renders an em-dash.
        sub: Optional muted context line under the value.
        delta: Optional signed change; green when >= 0, red when negative.
        pctl: Optional 0-100 percentile; adds the colored bar + label.

    Returns:
        HTML string for one tile.
    """
    delta_html = ""
    if delta is not None:
        color = COLOR_GOOD if delta >= 0 else COLOR_WEAK_SOFT
        delta_html = (
            f'<span style="font-size:11px;font-weight:600;color:{color};">{delta:+.1f}</span>'
        )
    sub_html = f'<div style="font-size:11px;color:{TEXT_MUTED};">{sub}</div>' if sub else ""
    pctl_html = ""
    if pctl is not None:
        pctl_html = (
            f'<div style="font-size:11px;font-weight:600;color:{pctl_text_color(pctl)};">'
            f"{pctl:.0f}th pctl</div>"
            f'<div style="height:4px;border-radius:2px;background:{BORDER};overflow:hidden;">'
            f'<div style="width:{pctl:.0f}%;height:100%;border-radius:2px;'
            f'background:{pctl_color(pctl)};"></div></div>'
        )
    return (
        f'<div style="background:{BG_TILE};border:1px solid {BORDER};border-radius:10px;'
        'padding:14px 16px 12px;display:flex;flex-direction:column;gap:6px;">'
        f'<div style="{_EYEBROW}">{label}</div>'
        '<div style="display:flex;align-items:baseline;gap:8px;">'
        f'<div style="font-family:{FONT_DISPLAY};font-size:34px;font-weight:800;'
        f'line-height:1;color:{TEXT};">{_display_value(value)}</div>'
        f"{delta_html}</div>{sub_html}{pctl_html}</div>"
    )


def render_stat_tile_row(tiles: list[dict], columns: int | None = None) -> None:
    """Render tiles side by side; each dict holds :func:`stat_tile_html` kwargs."""
    cols = st.columns(columns or len(tiles))
    for col, tile in zip(cols, tiles, strict=False):
        col.markdown(stat_tile_html(**tile), unsafe_allow_html=True)
