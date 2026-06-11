"""Unit tests for the shared team rail (logos, chips, selection state)."""

from __future__ import annotations

from dashboard.components.team_rail import build_rail_html, logo_url
from dashboard.components.theme import CONFERENCES, TEAM_ACCENTS


def _abbr_to_id() -> dict[str, int]:
    tricodes = CONFERENCES["WEST"] + CONFERENCES["EAST"]
    return {abbr: 1610612700 + i for i, abbr in enumerate(tricodes)}


def test_logo_url_points_at_nba_cdn() -> None:
    assert logo_url(1610612742) == "https://cdn.nba.com/logos/nba/1610612742/primary/L/logo.svg"


def test_rail_html_contains_all_30_logo_chips() -> None:
    mapping = _abbr_to_id()
    html = build_rail_html(mapping, selected="DAL")

    for abbr, team_id in mapping.items():
        assert f"?team={abbr}" in html  # every chip is clickable
        assert logo_url(team_id) in html  # every chip shows the CDN logo
    assert html.count("cdn.nba.com/logos") == 30
    assert "WEST" in html and "EAST" in html


def test_selected_chip_uses_team_accent_ring() -> None:
    mapping = _abbr_to_id()
    html = build_rail_html(mapping, selected="LAL")

    accent = TEAM_ACCENTS["LAL"]
    assert accent in html  # accent ring + glow on the selected chip
    # The selected chip is enlarged (40px vs the 32px idle chips).
    assert "width:40px" in html.replace(" ", "")
