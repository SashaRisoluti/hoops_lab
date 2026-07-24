"""Unit tests for the InfoTooltip component."""

from __future__ import annotations

from dashboard.components.info_tooltip import info_label_html


def test_definition_lands_in_title_attribute() -> None:
    html = info_label_html("TS%", "True shooting: PTS / (2 * (FGA + 0.44 * FTA)).")
    assert 'title="True shooting' in html
    assert "TS%" in html


def test_definition_quotes_are_escaped() -> None:
    html = info_label_html("PACE", 'Possessions per 48 minutes ("tempo").')
    assert '"tempo"' not in html  # raw quotes would break the attribute
    assert "&quot;tempo&quot;" in html
