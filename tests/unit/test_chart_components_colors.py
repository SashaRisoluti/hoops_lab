"""Color tests for the shared Plotly chart components after the restyle."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

# AppTest defaults to a 3s script timeout, which these apps can exceed on a loaded
# machine simply importing pandas and plotly. A generous ceiling keeps the suite
# deterministic while still failing on a genuine hang.
RUN_TIMEOUT = 30


def _radar_app() -> None:
    from dashboard.components.radar_chart import render_radar_chart

    render_radar_chart({"eFG%": 60.0, "TOV%": 40.0, "OREB%": 50.0}, title="Test")


def test_radar_uses_primary_palette_on_transparent_paper() -> None:
    at = AppTest.from_function(_radar_app).run(timeout=RUN_TIMEOUT)
    assert not at.exception
    fig = at.get("plotly_chart")[0].proto.spec
    assert "#F97316" not in fig
    assert "#4d7fff" in fig  # COLOR_PRIMARY_SOFT outline
    assert "rgba(0,82,255,0.25)" in fig  # hex_to_rgba(COLOR_PRIMARY, 0.25) fill


def _hist_app() -> None:
    import pandas as pd

    from dashboard.components.percentile_histogram import render_percentile_histogram

    df = pd.DataFrame(
        {"PLAYER_NAME": ["A", "B", "C"], "season": ["2025-26"] * 3, "PTS": [10.0, 20.0, 30.0]}
    )
    render_percentile_histogram(df, ["PTS"])


def test_histogram_uses_soft_primary_bars() -> None:
    at = AppTest.from_function(_hist_app).run(timeout=RUN_TIMEOUT)
    assert not at.exception
    spec = at.get("plotly_chart")[0].proto.spec
    assert "#4d7fff" in spec  # COLOR_PRIMARY_SOFT bars
    assert "crimson" not in spec
