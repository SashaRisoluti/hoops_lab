"""Unit tests for the Worldcup26 StatTile component."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from dashboard.components.stat_tile import stat_tile_html
from dashboard.components.theme import COLOR_GOOD, COLOR_WEAK_SOFT


def test_missing_value_renders_em_dash() -> None:
    # Spec section 5: None/NaN render an em-dash, never "None"/"nan".
    assert "—" in stat_tile_html("NET RATING", None)
    assert "—" in stat_tile_html("NET RATING", float("nan"))
    assert "None" not in stat_tile_html("NET RATING", None)


def test_delta_is_signed_and_colored() -> None:
    up = stat_tile_html("PACE", "99.1", delta=1.4)
    down = stat_tile_html("PACE", "99.1", delta=-2.0)
    assert "+1.4" in up and COLOR_GOOD in up
    assert "-2.0" in down and COLOR_WEAK_SOFT in down


def test_delta_zero_is_positive_signed_and_green() -> None:
    html = stat_tile_html("PACE", "99.1", delta=0.0)
    assert "+0.0" in html
    assert COLOR_GOOD in html


def test_pctl_adds_bar_and_label() -> None:
    html = stat_tile_html("OFF RATING", "118.4", pctl=80.0)
    assert "80th pctl" in html
    assert "width:80%" in html
    assert COLOR_GOOD in html  # 80th percentile bar is green


def test_sub_line_renders_when_given() -> None:
    html = stat_tile_html("TS%", "58.1", sub="league 4th")
    assert "league 4th" in html


def _row_app() -> None:
    from dashboard.components.stat_tile import render_stat_tile_row

    render_stat_tile_row(
        [
            {"label": "OFF RATING", "value": "118.4", "pctl": 80.0},
            {"label": "DEF RATING", "value": "110.2", "pctl": 55.0},
        ]
    )


def test_render_row_draws_without_exception() -> None:
    at = AppTest.from_function(_row_app).run()
    assert not at.exception
    assert len(at.columns) == 2


def _empty_row_app() -> None:
    from dashboard.components.stat_tile import render_stat_tile_row

    render_stat_tile_row([])


def test_render_row_empty_list_is_noop() -> None:
    at = AppTest.from_function(_empty_row_app).run()
    assert not at.exception
