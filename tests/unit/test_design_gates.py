"""Permanent design-system gates: token single-source-of-truth stays true."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dashboard.components import theme
from hoops_lab.visuals import altair_charts, court, shot_maps

REPO = Path(__file__).resolve().parents[2]
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def test_no_hex_literals_in_dashboard_outside_theme() -> None:
    offenders: list[str] = []
    for path in (REPO / "dashboard").rglob("*.py"):
        if path.name == "theme.py":
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if HEX_RE.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{i}")
    assert not offenders, f"hex literals outside theme.py: {offenders}"


def test_visuals_mirror_matches_theme_tokens() -> None:
    assert altair_charts.COLOR_GOOD == theme.COLOR_GOOD
    assert altair_charts.COLOR_MID == theme.COLOR_MID
    assert altair_charts.COLOR_WEAK == theme.COLOR_WEAK
    assert altair_charts.BG_CARD == theme.BG_CARD
    assert altair_charts.GRID == theme.GRID
    assert altair_charts.TEXT == theme.TEXT
    assert altair_charts.TEXT_MUTED == theme.TEXT_SOFT
    assert court.COURT_BG == theme.BG_CARD
    assert court.COURT_LINE == theme.COURT_LINE
    assert shot_maps.MADE_COLOR == theme.COLOR_GOOD
    assert shot_maps.MISS_COLOR == theme.COLOR_WEAK


def test_streamlit_config_matches_tokens() -> None:
    config = tomllib.loads((REPO / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["theme"]["primaryColor"] == theme.COLOR_PRIMARY
    assert config["theme"]["backgroundColor"] == theme.BG_PAGE
    assert config["theme"]["secondaryBackgroundColor"] == theme.BG_CARD
    assert config["theme"]["textColor"] == theme.TEXT


def test_legacy_names_are_gone() -> None:
    for name in ("ORANGE", "BLUE", "BLUE_TEXT", "RED", "RED_TEXT"):
        assert not hasattr(theme, name), f"legacy alias {name} still exists"
    from dashboard.components import overview_cards

    assert not hasattr(overview_cards, "kpi_card")
    assert not hasattr(overview_cards, "stat_tile")  # renamed to mini_tile
    assert hasattr(overview_cards, "mini_tile")
