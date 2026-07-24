"""Smoke tests: the shell chrome renders under AppTest without exceptions."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _shell_app() -> None:
    from dashboard.components.theme import inject_theme, render_command_bar

    inject_theme()
    render_command_bar("Overview")


def test_shell_chrome_renders_without_exception() -> None:
    at = AppTest.from_function(_shell_app).run()
    assert not at.exception


def test_injected_css_loads_inter_fonts() -> None:
    at = AppTest.from_function(_shell_app).run()
    blob = "".join(m.value for m in at.markdown)
    assert "Inter+Tight" in blob
    assert "Barlow" not in blob
