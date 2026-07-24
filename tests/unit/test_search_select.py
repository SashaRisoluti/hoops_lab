"""Unit tests for the SearchSelect component."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from dashboard.components.search_select import entity_label


def test_entity_label_formats_meta() -> None:
    assert entity_label("Luka Doncic", "DAL · G") == "Luka Doncic · DAL · G"
    assert entity_label("Luka Doncic") == "Luka Doncic"


def _picker_app() -> None:
    import streamlit as st

    from dashboard.components.search_select import search_select

    choice = search_select("Team", ["BOS", "DAL", "LAL"], key="pick_team")
    st.write(choice)


def test_search_select_returns_default_selection() -> None:
    at = AppTest.from_function(_picker_app).run()
    assert not at.exception
    assert at.selectbox[0].value == "BOS"


def test_search_select_switches_selection() -> None:
    at = AppTest.from_function(_picker_app).run()
    at.selectbox[0].select("LAL").run()
    assert at.selectbox[0].value == "LAL"
