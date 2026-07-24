"""Metric-definition tooltips (design spec 2026-07-24, section 2).

Uses the native browser tooltip (title attribute): zero JS, works inside
any HTML builder string.
"""

from __future__ import annotations

import html as html_lib

from dashboard.components.theme import TEXT_MUTED


def info_label_html(label: str, definition: str) -> str:
    """Wrap a stat label with a hoverable metric definition.

    Args:
        label: Visible label text.
        definition: Plain-text metric definition shown on hover.

    Returns:
        HTML string: label + small info glyph with a title tooltip.
    """
    tooltip = html_lib.escape(definition, quote=True)
    return (
        f'<span title="{tooltip}" style="cursor:help;'
        f'border-bottom:1px dotted {TEXT_MUTED};">{label}&nbsp;'
        f'<span style="font-size:10px;color:{TEXT_MUTED};">ⓘ</span></span>'
    )
