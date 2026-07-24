"""Unit tests for the PageHeader component."""

from __future__ import annotations

from dashboard.components.page_header import page_header_html
from dashboard.components.theme import FONT_DISPLAY


def test_title_uses_display_font() -> None:
    html = page_header_html("Team Overview")
    assert "Team Overview" in html
    assert FONT_DISPLAY in html


def test_subtitle_and_chips_render_when_given() -> None:
    html = page_header_html("Shot Map", subtitle="2025-26", context_chips=["DAL", "2025-26"])
    assert "2025-26" in html
    assert html.count("border-radius:999px") == 2  # one pill per chip


def test_optional_parts_absent_by_default() -> None:
    html = page_header_html("Lineups")
    assert "border-radius:999px" not in html
