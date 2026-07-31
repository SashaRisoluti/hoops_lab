"""The design tokens the web app consumes stay identical to the Streamlit ones."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard.components.theme import TEAM_ACCENTS_READABLE, TOKENS
from scripts.export_web_data import TOKENS_PATH, export_tokens

REPO = Path(__file__).resolve().parents[2]


def test_export_writes_the_theme_tokens(tmp_path: Path) -> None:
    dest = tmp_path / "tokens.json"
    export_tokens(dest)
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["tokens"] == TOKENS


def test_export_writes_the_readable_team_accents(tmp_path: Path) -> None:
    dest = tmp_path / "tokens.json"
    export_tokens(dest)
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["teamAccents"] == TEAM_ACCENTS_READABLE


def test_export_records_where_the_tokens_came_from(tmp_path: Path) -> None:
    dest = tmp_path / "tokens.json"
    export_tokens(dest)
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["generatedFrom"] == "dashboard/components/theme.py"


def test_export_creates_missing_parent_directories(tmp_path: Path) -> None:
    dest = tmp_path / "web" / "nested" / "tokens.json"
    export_tokens(dest)
    assert dest.exists()


def test_export_is_deterministic(tmp_path: Path) -> None:
    # A timestamp here would produce a diff on every run and make the drift gate useless.
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    export_tokens(first)
    export_tokens(second)
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_export_overwrites_an_existing_file(tmp_path: Path) -> None:
    dest = tmp_path / "tokens.json"
    dest.write_text("stale", encoding="utf-8")
    export_tokens(dest)
    assert json.loads(dest.read_text(encoding="utf-8"))["tokens"] == TOKENS


# The drift gate that compares the committed artifact against theme.py lives in
# test_design_gates.py, alongside the other single-source-of-truth guards.
def test_the_committed_artifact_lives_where_the_web_app_expects_it() -> None:
    assert TOKENS_PATH == "web/tokens.json"
    assert (REPO / TOKENS_PATH).exists()
