"""Color tests for the shared Plotly chart components after the restyle."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _radar_app() -> None:
    from dashboard.components.radar_chart import render_radar_chart

    render_radar_chart({"eFG%": 60.0, "TOV%": 40.0, "OREB%": 50.0}, title="Test")


def test_radar_uses_primary_palette_on_transparent_paper() -> None:
    at = AppTest.from_function(_radar_app).run()
    assert not at.exception
    fig = at.get("plotly_chart")[0].proto.spec
    assert "#F97316" not in fig
    assert "#4d7fff" in fig  # COLOR_PRIMARY_SOFT outline
    assert "rgba(0,82,255,0.25)" in fig  # hex_to_rgba(COLOR_PRIMARY, 0.25) fill
