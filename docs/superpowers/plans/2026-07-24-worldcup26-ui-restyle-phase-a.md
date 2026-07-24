# Worldcup26 UI Restyle — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the hoops-lab Streamlit dashboard core (tokens, shell chrome, component system, Overview page) to the Worldcup26 visual language.

**Architecture:** In-place token swap in `dashboard/components/theme.py` with semantic names (`COLOR_GOOD`/`COLOR_MID`/`COLOR_WEAK`/`COLOR_PRIMARY`); legacy names stay as aliases so the 9 unmigrated pages render the new palette immediately. Four new pure-render components. Overview (`dashboard/app.py`) migrates onto them. Spec: `docs/superpowers/specs/2026-07-24-worldcup26-ui-restyle-design.md`.

**Tech Stack:** Python 3.11, Streamlit, Plotly, pytest (+ `streamlit.testing.v1.AppTest`), ruff.

## Global Constraints

- Interpreter: `.venv\Scripts\python.exe`; run everything from the repo root.
- Line length 100 (ruff). After each task: `ruff check --fix . ; ruff format .`
- Type hints on all public functions; Google-style docstrings; code and docstrings in English.
- Components in `dashboard/components/` never call the database; builders return HTML strings, `render_*` wrappers return `None`.
- Unit tests never hit the network or the DB.
- New rule this project introduces: hex color literals live ONLY in `theme.py` (Phase B enforces by grep; do not add new hex literals outside it now).
- Palette (spec, exact): surfaces `#070b14 #0b0f19 #0f172a #141c2e`, borders `#111829 #0e1320`, good `#16c47f`, mid `#ffd100`, weak `#e0262c`, primary `#0052ff`, special `#a855f7`, text `#f1f5f9 #9ca3af #64748b`. Fonts Inter 400–900 / Inter Tight 700–900 / ui-monospace.
- `TEAM_ACCENTS` and `CONFERENCES` in `theme.py` must NOT change.
- Note: the spec's `BORDER_SOFT #0e1320` maps to code token `BORDER_DARK` — in the existing code `_SOFT` is the *lightest* border (rail chips), `_DARK` the darkest. Values used here: `BORDER_DARK #0e1320`, `BORDER #111829`, `BORDER_SOFT #1a2338`.

---

### Task 1: Semantic design tokens in `theme.py`

**Files:**
- Modify: `dashboard/components/theme.py`
- Create: `tests/unit/test_theme_tokens.py`
- Modify: `tests/unit/test_overview.py:7-28`

**Interfaces:**
- Produces (consumed by every later task):
  - `COLOR_GOOD = "#16c47f"`, `COLOR_MID = "#ffd100"`, `COLOR_WEAK = "#e0262c"`,
    `COLOR_PRIMARY = "#0052ff"`, `COLOR_SPECIAL = "#a855f7"`,
    `COLOR_PRIMARY_SOFT = "#4d7fff"`, `COLOR_WEAK_SOFT = "#ff5a63"`
  - Surfaces/text: `BG_PAGE BG_FRAME BG_BAR BG_CARD BG_TILE BORDER_DARK BORDER BORDER_SOFT GRID COURT_LINE TEXT TEXT_SOFT TEXT_MUTED TEXT_FAINT` (same names as today, new values)
  - `pctl_color(percentile: float) -> str`, `pctl_text_color(percentile: float) -> str` (same signatures, new return values)
  - `PLOTLY_TEMPLATE: dict` — kwargs for `fig.update_layout(**PLOTLY_TEMPLATE)`
  - `TOKENS: dict[str, str]`, `tokens_json() -> str`
  - Aliases: `ORANGE=COLOR_GOOD`, `BLUE=COLOR_MID`, `BLUE_TEXT=COLOR_PRIMARY_SOFT`, `RED=COLOR_WEAK`, `RED_TEXT=COLOR_WEAK_SOFT`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_theme_tokens.py`:

```python
"""Unit tests for the Worldcup26 design tokens (spec 2026-07-24)."""

from __future__ import annotations

import json

from dashboard.components.theme import (
    BLUE,
    COLOR_GOOD,
    COLOR_MID,
    COLOR_PRIMARY,
    COLOR_WEAK,
    COLOR_WEAK_SOFT,
    ORANGE,
    PLOTLY_TEMPLATE,
    RED,
    TOKENS,
    pctl_color,
    pctl_text_color,
    tokens_json,
)


def test_worldcup26_palette_values() -> None:
    assert COLOR_GOOD == "#16c47f"
    assert COLOR_MID == "#ffd100"
    assert COLOR_WEAK == "#e0262c"
    assert COLOR_PRIMARY == "#0052ff"


def test_pctl_color_boundaries() -> None:
    # Spec rule: >=66 good, 33-66 mid, <33 weak — thresholds unchanged.
    assert pctl_color(100) == COLOR_GOOD
    assert pctl_color(66) == COLOR_GOOD
    assert pctl_color(65.9) == COLOR_MID
    assert pctl_color(33) == COLOR_MID
    assert pctl_color(32.9) == COLOR_WEAK
    assert pctl_color(0) == COLOR_WEAK


def test_pctl_text_color_readable_variants() -> None:
    assert pctl_text_color(80) == COLOR_GOOD
    assert pctl_text_color(50) == COLOR_MID
    assert pctl_text_color(10) == COLOR_WEAK_SOFT


def test_legacy_aliases_point_at_new_tokens() -> None:
    # Phase A aliases keep unmigrated pages on the new palette; deleted in Phase B.
    assert ORANGE == COLOR_GOOD
    assert BLUE == COLOR_MID
    assert RED == COLOR_WEAK


def test_tokens_json_roundtrip() -> None:
    payload = json.loads(tokens_json())
    assert payload == TOKENS
    assert payload["primary"] == "#0052ff"
    assert payload["good"] == "#16c47f"


def test_plotly_template_uses_inter_on_transparent_paper() -> None:
    assert "Inter" in PLOTLY_TEMPLATE["font"]["family"]
    assert PLOTLY_TEMPLATE["paper_bgcolor"] == "rgba(0,0,0,0)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_tokens.py -q`
Expected: FAIL — `ImportError: cannot import name 'COLOR_GOOD'`

- [ ] **Step 3: Rewrite the token block in `theme.py`**

Replace the module docstring (lines 1–8) with:

```python
"""Design system — Worldcup26 restyle (spec docs/superpowers/specs/2026-07-24).

Deep navy surfaces with a fixed data-color language:
**green = good (>=66th pctl), yellow = mid (33rd-66th), red = weak (<33rd)** —
the same semantics on every chart so any reader decodes them instantly.
Electric blue is the primary/interactive color (selection, nav active).
Team accents re-theme the rail ring, header stripe and logo only; the
data-color language never changes.
"""
```

Replace lines 14–38 (the token block from `# ---- Tokens` through `FONT_MONO`) with:

```python
# ---- Surfaces (Worldcup26 navy family) --------------------------------------
BG_PAGE = "#070b14"
BG_FRAME = "#0b0f19"
BG_BAR = "#0b0f19"
BG_CARD = "#0f172a"
BG_TILE = "#141c2e"
BORDER_DARK = "#0e1320"
BORDER = "#111829"
BORDER_SOFT = "#1a2338"
GRID = "#1c2740"
COURT_LINE = "#33415e"
TEXT = "#f1f5f9"
TEXT_SOFT = "#9ca3af"
TEXT_MUTED = "#64748b"
TEXT_FAINT = "#475569"

# ---- Data semantics ---------------------------------------------------------
COLOR_GOOD = "#16c47f"  # >=66th percentile
COLOR_MID = "#ffd100"  # 33rd-66th percentile
COLOR_WEAK = "#e0262c"  # <33rd percentile
COLOR_PRIMARY = "#0052ff"  # selection, nav active, interactive elements
COLOR_SPECIAL = "#a855f7"  # model/AI-derived flags
COLOR_PRIMARY_SOFT = "#4d7fff"  # readable primary for small text / thin lines
COLOR_WEAK_SOFT = "#ff5a63"  # readable weak for small text

# ---- Legacy aliases (Phase A only — deleted in Phase B) ---------------------
ORANGE = COLOR_GOOD
BLUE = COLOR_MID
BLUE_TEXT = COLOR_PRIMARY_SOFT
RED = COLOR_WEAK
RED_TEXT = COLOR_WEAK_SOFT

FONT_BODY = "Inter, sans-serif"
FONT_DISPLAY = "'Inter Tight', sans-serif"
FONT_MONO = "ui-monospace, monospace"
```

Add `import json` after `from __future__ import annotations` (before `import streamlit as st`).

- [ ] **Step 4: Update `pctl_color`/`pctl_text_color` and add `TOKENS`, `tokens_json`, `PLOTLY_TEMPLATE`**

Replace the two existing functions with:

```python
def pctl_color(percentile: float) -> str:
    """Bar/marker color for a league percentile (fixed data-color rule)."""
    if percentile >= 66:
        return COLOR_GOOD
    if percentile >= 33:
        return COLOR_MID
    return COLOR_WEAK


def pctl_text_color(percentile: float) -> str:
    """Readable text variant of :func:`pctl_color`."""
    if percentile >= 66:
        return COLOR_GOOD
    if percentile >= 33:
        return COLOR_MID
    return COLOR_WEAK_SOFT
```

Immediately after `pctl_text_color`, add:

```python
#: Design tokens as one portable mapping (React/Tailwind port seed).
TOKENS: dict[str, str] = {
    "bg_page": BG_PAGE,
    "bg_frame": BG_FRAME,
    "bg_card": BG_CARD,
    "bg_tile": BG_TILE,
    "border": BORDER,
    "border_dark": BORDER_DARK,
    "border_soft": BORDER_SOFT,
    "grid": GRID,
    "court_line": COURT_LINE,
    "text": TEXT,
    "text_soft": TEXT_SOFT,
    "text_muted": TEXT_MUTED,
    "text_faint": TEXT_FAINT,
    "good": COLOR_GOOD,
    "mid": COLOR_MID,
    "weak": COLOR_WEAK,
    "primary": COLOR_PRIMARY,
    "special": COLOR_SPECIAL,
    "primary_soft": COLOR_PRIMARY_SOFT,
    "weak_soft": COLOR_WEAK_SOFT,
    "font_body": FONT_BODY,
    "font_display": FONT_DISPLAY,
    "font_mono": FONT_MONO,
}


def tokens_json() -> str:
    """Serialize the design tokens to JSON (React/Tailwind port seed)."""
    return json.dumps(TOKENS, indent=2)


#: Shared Plotly layout kwargs — every figure calls update_layout(**PLOTLY_TEMPLATE).
PLOTLY_TEMPLATE: dict = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=FONT_BODY, color=TEXT),
    margin=dict(l=10, r=10, t=10, b=10),
)
```

- [ ] **Step 5: Update the stale tricolor test in `tests/unit/test_overview.py`**

Replace the import block (lines 7–14) and the first test (lines 22–28) with:

```python
from dashboard.components.theme import (
    COLOR_GOOD,
    COLOR_MID,
    COLOR_WEAK,
    CONFERENCES,
    TEAM_ACCENTS,
    pctl_color,
)
```

```python
def test_pctl_color_semantic_buckets() -> None:
    # Design rule: green = good (>=66th), yellow = mid (33-66), red = weak (<33rd).
    assert pctl_color(82) == COLOR_GOOD
    assert pctl_color(66) == COLOR_GOOD
    assert pctl_color(50) == COLOR_MID
    assert pctl_color(33) == COLOR_MID
    assert pctl_color(20) == COLOR_WEAK
```

(The other tests in the file — team maps, zone buckets, flags, standings — stay untouched.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_tokens.py tests/unit/test_overview.py -q`
Expected: PASS (all).

- [ ] **Step 7: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/theme.py tests/unit/test_theme_tokens.py tests/unit/test_overview.py
git commit -m "feat(theme): Worldcup26 semantic design tokens with legacy aliases"
```

---

### Task 2: Shell chrome — config.toml, fonts, nav, rail CSS

**Files:**
- Modify: `.streamlit/config.toml`
- Modify: `dashboard/components/theme.py` (`inject_theme`, `render_command_bar`)
- Create: `tests/unit/test_theme_shell.py`

**Interfaces:**
- Consumes: Task 1 tokens.
- Produces: `inject_theme() -> None` and `render_command_bar(active: str) -> None` (signatures unchanged; only CSS/colors change). Pages keep calling them exactly as today.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_theme_shell.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_shell.py -q`
Expected: `test_shell_chrome_renders_without_exception` PASSES already (chrome renders with old fonts); `test_injected_css_loads_inter_fonts` FAILS on `assert "Inter+Tight" in blob`.

- [ ] **Step 3: Update `.streamlit/config.toml`**

Full new content:

```toml
[theme]
base = "dark"
primaryColor = "#0052ff"
backgroundColor = "#070b14"
secondaryBackgroundColor = "#0f172a"
textColor = "#f1f5f9"

[client]
showSidebarNavigation = false
```

- [ ] **Step 4: Update `inject_theme` CSS**

Replace the whole `st.markdown(...)` payload inside `inject_theme` with:

```python
    st.markdown(
        f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Inter+Tight:wght@700;800;900&display=swap" rel="stylesheet">
<style>
  html, body, [data-testid="stAppViewContainer"] {{
    background: {BG_PAGE}; font-family: {FONT_BODY}; color: {TEXT};
  }}
  [data-testid="stHeader"] {{ background: {BG_PAGE}; }}
  h1, h2, h3 {{ font-family: {FONT_DISPLAY}; font-weight: 800; letter-spacing: -0.01em; }}
  [data-testid="stSidebar"] {{ background: {BG_BAR}; border-right: 1px solid {BORDER_DARK}; }}
  /* Command bar page links */
  div[data-testid="stPageLink"] a {{
    font-size: 13px; font-weight: 500; color: {TEXT_MUTED} !important;
    padding: 4px 12px; border-radius: 7px; text-decoration: none;
  }}
  div[data-testid="stPageLink"] a:hover {{ color: {TEXT} !important; background: {BG_TILE}; }}
  div[data-testid="stPageLink"] a[aria-current="page"] {{
    color: {TEXT} !important; background: {BG_TILE}; box-shadow: inset 0 -2px 0 {COLOR_PRIMARY};
  }}
  /* Team-rail buttons: circular tricode chips */
  div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    width: 34px; height: 34px; min-height: 34px; padding: 0; border-radius: 50%;
    background: {BG_CARD}; border: 1px solid {BORDER_SOFT};
    font-family: {FONT_MONO}; font-size: 9px; color: {TEXT_MUTED};
  }}
  div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    border-color: {COLOR_PRIMARY_SOFT}; color: {TEXT};
  }}
</style>
""",
        unsafe_allow_html=True,
    )
```

Notes: uppercase transform on `h1-h3` is dropped (Worldcup26 uses bold Inter Tight, mixed case); hover/active backgrounds use `BG_TILE` instead of the old hardcoded `#161B23`/`#1A1F29`; active underline is `COLOR_PRIMARY`.

- [ ] **Step 5: Update `render_command_bar` logo mark**

In the first `cols[0].markdown(...)` HTML, change the logo circle from `background:{ORANGE}` to `background:{COLOR_PRIMARY}`, and the two crossing lines keep `background:{BG_BAR}`. The logo wordmark div: change `font-weight:700` to `font-weight:800` and remove nothing else. (These are the only edits in this function.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_shell.py -q`
Expected: PASS (2 tests).

- [ ] **Step 7: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add .streamlit/config.toml dashboard/components/theme.py tests/unit/test_theme_shell.py
git commit -m "feat(theme): navy shell chrome, Inter fonts, primary-blue nav"
```

---

### Task 3: StatTile component

**Files:**
- Create: `dashboard/components/stat_tile.py`
- Create: `tests/unit/test_stat_tile.py`

**Interfaces:**
- Consumes: Task 1 tokens (`BG_TILE`, `BORDER`, `COLOR_GOOD`, `COLOR_WEAK_SOFT`, `FONT_DISPLAY`, `FONT_MONO`, `TEXT`, `TEXT_MUTED`, `pctl_color`, `pctl_text_color`).
- Produces (consumed by Task 8 and by Phase B pages):
  - `stat_tile_html(label: str, value: str | float | None, sub: str | None = None, delta: float | None = None, pctl: float | None = None) -> str`
  - `render_stat_tile_row(tiles: list[dict], columns: int | None = None) -> None` — each dict holds `stat_tile_html` kwargs.
- NOTE: `overview_cards.py` already has a SMALLER function named `stat_tile` (legacy mono tile). It stays untouched; call sites always module-qualify (`cards.stat_tile` vs `stat_tile.stat_tile_html`), so there is no collision. The legacy one is removed in Phase B.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_stat_tile.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_stat_tile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.components.stat_tile'`

- [ ] **Step 3: Write the component**

Create `dashboard/components/stat_tile.py`:

```python
"""Worldcup26-style stat tiles (design spec 2026-07-24, section 2).

Pure render helpers: the builder returns an HTML string, the render
wrapper draws tiles into Streamlit columns and returns None. No database
access — data arrives already formatted.
"""

from __future__ import annotations

import math

import streamlit as st

from dashboard.components.theme import (
    BG_TILE,
    BORDER,
    COLOR_GOOD,
    COLOR_WEAK_SOFT,
    FONT_DISPLAY,
    FONT_MONO,
    TEXT,
    TEXT_MUTED,
    pctl_color,
    pctl_text_color,
)

_EYEBROW = f"font-family:{FONT_MONO};font-size:10px;letter-spacing:0.12em;color:{TEXT_MUTED};"


def _display_value(value: str | float | None) -> str:
    """Missing data renders as an em-dash (spec section 5)."""
    if value is None:
        return "—"
    if isinstance(value, float) and math.isnan(value):
        return "—"
    return str(value)


def stat_tile_html(
    label: str,
    value: str | float | None,
    sub: str | None = None,
    delta: float | None = None,
    pctl: float | None = None,
) -> str:
    """Build one stat tile.

    Args:
        label: Uppercase eyebrow label.
        value: Main value, pre-formatted; None/NaN renders an em-dash.
        sub: Optional muted context line under the value.
        delta: Optional signed change; green when >= 0, red when negative.
        pctl: Optional 0-100 percentile; adds the colored bar + label.

    Returns:
        HTML string for one tile.
    """
    delta_html = ""
    if delta is not None:
        color = COLOR_GOOD if delta >= 0 else COLOR_WEAK_SOFT
        delta_html = (
            f'<span style="font-size:11px;font-weight:600;color:{color};">{delta:+.1f}</span>'
        )
    sub_html = f'<div style="font-size:11px;color:{TEXT_MUTED};">{sub}</div>' if sub else ""
    pctl_html = ""
    if pctl is not None:
        pctl_html = (
            f'<div style="font-size:11px;font-weight:600;color:{pctl_text_color(pctl)};">'
            f"{pctl:.0f}th pctl</div>"
            f'<div style="height:4px;border-radius:2px;background:{BORDER};overflow:hidden;">'
            f'<div style="width:{pctl:.0f}%;height:100%;border-radius:2px;'
            f'background:{pctl_color(pctl)};"></div></div>'
        )
    return (
        f'<div style="background:{BG_TILE};border:1px solid {BORDER};border-radius:10px;'
        'padding:14px 16px 12px;display:flex;flex-direction:column;gap:6px;">'
        f'<div style="{_EYEBROW}">{label}</div>'
        '<div style="display:flex;align-items:baseline;gap:8px;">'
        f'<div style="font-family:{FONT_DISPLAY};font-size:34px;font-weight:800;'
        f'line-height:1;color:{TEXT};">{_display_value(value)}</div>'
        f"{delta_html}</div>{sub_html}{pctl_html}</div>"
    )


def render_stat_tile_row(tiles: list[dict], columns: int | None = None) -> None:
    """Render tiles side by side; each dict holds :func:`stat_tile_html` kwargs."""
    cols = st.columns(columns or len(tiles))
    for col, tile in zip(cols, tiles, strict=False):
        col.markdown(stat_tile_html(**tile), unsafe_allow_html=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_stat_tile.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/stat_tile.py tests/unit/test_stat_tile.py
git commit -m "feat(components): StatTile with delta, sub-line and percentile bar"
```

---

### Task 4: PageHeader component

**Files:**
- Create: `dashboard/components/page_header.py`
- Create: `tests/unit/test_page_header.py`

**Interfaces:**
- Consumes: Task 1 tokens (`BG_TILE`, `BORDER`, `FONT_DISPLAY`, `FONT_MONO`, `TEXT`, `TEXT_MUTED`, `TEXT_SOFT`).
- Produces (consumed by Task 8 and Phase B pages):
  - `page_header_html(title: str, subtitle: str | None = None, context_chips: list[str] | None = None) -> str`
  - `render_page_header(title: str, subtitle: str | None = None, context_chips: list[str] | None = None) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_page_header.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_page_header.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.components.page_header'`

- [ ] **Step 3: Write the component**

Create `dashboard/components/page_header.py`:

```python
"""Consistent page header (design spec 2026-07-24, section 2).

Pure render: builder returns HTML, wrapper draws it and returns None.
"""

from __future__ import annotations

import streamlit as st

from dashboard.components.theme import (
    BG_TILE,
    BORDER,
    FONT_DISPLAY,
    FONT_MONO,
    TEXT,
    TEXT_MUTED,
    TEXT_SOFT,
)


def page_header_html(
    title: str,
    subtitle: str | None = None,
    context_chips: list[str] | None = None,
) -> str:
    """Build the page header block.

    Args:
        title: Page title (Inter Tight display).
        subtitle: Optional muted line under the title.
        context_chips: Optional small mono pills on the right (season, team...).

    Returns:
        HTML string for the header block.
    """
    subtitle_html = (
        f'<div style="font-size:13px;color:{TEXT_MUTED};">{subtitle}</div>' if subtitle else ""
    )
    chips_html = ""
    if context_chips:
        chips = "".join(
            f'<span style="font-family:{FONT_MONO};font-size:10px;letter-spacing:0.08em;'
            f"color:{TEXT_SOFT};background:{BG_TILE};border:1px solid {BORDER};"
            f'border-radius:999px;padding:3px 10px;">{chip}</span>'
            for chip in context_chips
        )
        chips_html = f'<div style="display:flex;gap:6px;">{chips}</div>'
    return (
        '<div style="display:flex;align-items:flex-end;justify-content:space-between;'
        'margin:2px 0 14px;">'
        f'<div><div style="font-family:{FONT_DISPLAY};font-size:26px;font-weight:800;'
        f'letter-spacing:-0.01em;color:{TEXT};">{title}</div>{subtitle_html}</div>'
        f"{chips_html}</div>"
    )


def render_page_header(
    title: str,
    subtitle: str | None = None,
    context_chips: list[str] | None = None,
) -> None:
    """Draw the page header into the current Streamlit container."""
    st.markdown(page_header_html(title, subtitle, context_chips), unsafe_allow_html=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_page_header.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/page_header.py tests/unit/test_page_header.py
git commit -m "feat(components): PageHeader with subtitle and context chips"
```

---

### Task 5: InfoTooltip component

**Files:**
- Create: `dashboard/components/info_tooltip.py`
- Create: `tests/unit/test_info_tooltip.py`

**Interfaces:**
- Consumes: Task 1 tokens (`TEXT_MUTED`).
- Produces (consumed by Phase B pages): `info_label_html(label: str, definition: str) -> str` — inline label with a native browser tooltip carrying the metric definition.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_info_tooltip.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_info_tooltip.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.components.info_tooltip'`

- [ ] **Step 3: Write the component**

Create `dashboard/components/info_tooltip.py`:

```python
"""Metric-definition tooltips (design spec 2026-07-24, section 2).

Uses the native browser tooltip (title attribute): zero JS, works inside
any HTML builder string.
"""

from __future__ import annotations

import html as html_lib

from dashboard.components.theme import TEXT_MUTED


def info_label_html(label: str, definition: str) -> str:
    """Wrap a stat label with a hoverable metric definition.

    Args:
        label: Visible label text.
        definition: Plain-text metric definition shown on hover.

    Returns:
        HTML string: label + small info glyph with a title tooltip.
    """
    tooltip = html_lib.escape(definition, quote=True)
    return (
        f'<span title="{tooltip}" style="cursor:help;'
        f'border-bottom:1px dotted {TEXT_MUTED};">{label}&nbsp;'
        f'<span style="font-size:10px;color:{TEXT_MUTED};">ⓘ</span></span>'
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_info_tooltip.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/info_tooltip.py tests/unit/test_info_tooltip.py
git commit -m "feat(components): InfoTooltip metric-definition labels"
```

---

### Task 6: SearchSelect component

**Files:**
- Create: `dashboard/components/search_select.py`
- Create: `tests/unit/test_search_select.py`

**Interfaces:**
- Consumes: nothing beyond Streamlit.
- Produces (consumed by Phase B pages):
  - `entity_label(name: str, meta: str | None = None) -> str`
  - `search_select(label, options, format_func=str, key=None, index=0, help_text=None)` returning the selected option (input widgets return the selection — same contract as `team_rail`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_search_select.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_search_select.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.components.search_select'`

- [ ] **Step 3: Write the component**

Create `dashboard/components/search_select.py`:

```python
"""Standardized searchable entity picker (design spec 2026-07-24, section 2).

Wraps st.selectbox (which ships type-to-search) so every page gets the
same picker UX and label formatting. Input widgets return the selection —
same contract as team_rail.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

import streamlit as st

T = TypeVar("T")


def entity_label(name: str, meta: str | None = None) -> str:
    """'Name · meta' display label; plain name when meta is missing."""
    return f"{name} · {meta}" if meta else name


def search_select(
    label: str,
    options: Sequence[T],
    format_func: Callable[[T], str] = str,
    key: str | None = None,
    index: int = 0,
    help_text: str | None = None,
) -> T:
    """Searchable selectbox with the shared picker semantics.

    Args:
        label: Widget label.
        options: Selectable values (ids or plain strings).
        format_func: Maps an option to its display label (use entity_label).
        key: Session-state key (pages prefix with their page name).
        index: Default selected index.
        help_text: Optional help tooltip.

    Returns:
        The selected option.
    """
    return st.selectbox(
        label,
        options,
        index=index,
        format_func=format_func,
        key=key,
        help=help_text,
        placeholder="Search…",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_search_select.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/search_select.py tests/unit/test_search_select.py
git commit -m "feat(components): SearchSelect standardized entity picker"
```

---

### Task 7: `overview_cards.py` onto the shared template and semantic colors

**Files:**
- Modify: `dashboard/components/overview_cards.py`
- Create: `tests/unit/test_overview_cards_colors.py`

**Interfaces:**
- Consumes: Task 1 (`PLOTLY_TEMPLATE`, semantic color tokens, `hex_to_rgba`).
- Produces: all existing builder signatures UNCHANGED (`card_title`, `kpi_card`, `team_band`, `flag_box`, `leader_rows`, `factor_rows`, `tricolor_legend`, `zone_tile`, `stat_tile`, `radar_figure`, `wp_figure`, `form_figure`) — only colors/fonts inside change. Task 8 and unmigrated pages keep calling them as today.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_overview_cards_colors.py`:

```python
"""Color-semantics tests for the Overview builders after the restyle."""

from __future__ import annotations

from dashboard.components.overview_cards import flag_box, radar_figure, tricolor_legend
from dashboard.components.theme import COLOR_GOOD, COLOR_MID, COLOR_PRIMARY, COLOR_WEAK


def test_flag_box_low_is_informational_blue() -> None:
    # LOW flags are informational -> primary blue, NOT the mid-percentile yellow.
    assert COLOR_PRIMARY in flag_box("LOW", "steady form")


def test_flag_box_high_is_weak_red() -> None:
    assert COLOR_WEAK in flag_box("HIGH", "cold shooting")


def test_legend_shows_semantic_triple() -> None:
    html = tricolor_legend()
    assert COLOR_GOOD in html
    assert COLOR_MID in html
    assert COLOR_WEAK in html


def test_radar_fill_derives_from_primary() -> None:
    fig = radar_figure({"eFG%": 60.0, "TOV": 40.0, "ORB": 50.0})
    assert fig.data[0].fillcolor == "rgba(0,82,255,0.32)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_overview_cards_colors.py -q`
Expected: FAIL — `test_flag_box_low_is_informational_blue` (LOW currently maps to the BLUE alias = yellow) and `test_radar_fill_derives_from_primary` (fill is the old hardcoded `rgba(46,95,183,0.32)`).

- [ ] **Step 3: Rewire imports and colors**

In `dashboard/components/overview_cards.py`:

1. Replace the import block from `dashboard.components.theme` with:

```python
from dashboard.components.theme import (
    BG_CARD,
    BG_TILE,
    BORDER,
    COLOR_GOOD,
    COLOR_MID,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SOFT,
    COLOR_WEAK,
    COLOR_WEAK_SOFT,
    FONT_DISPLAY,
    FONT_MONO,
    GRID,
    PLOTLY_TEMPLATE,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    TEXT_SOFT,
    hex_to_rgba,
    pctl_color,
    pctl_text_color,
)
```

2. Replace the `_PLOTLY_BASE = dict(...)` block with:

```python
_PLOTLY_BASE = dict(PLOTLY_TEMPLATE)
```

3. Mechanical renames in the function bodies (aliases made them equivalent; this makes it explicit before Phase B deletes the aliases):
   - `team_band` chips: `ORANGE` → `COLOR_GOOD` (both occurrences), `RED` → `COLOR_WEAK`, `RED_TEXT` → `COLOR_WEAK_SOFT`.
   - `flag_box` palette dict becomes:

```python
    palette = {
        "HIGH": (COLOR_WEAK, COLOR_WEAK_SOFT, 0.10, 0.45),
        "MED": (COLOR_MID, COLOR_MID, 0.08, 0.40),
        "LOW": (COLOR_PRIMARY, COLOR_PRIMARY_SOFT, 0.08, 0.40),
    }
```

   - `tricolor_legend`: `chip(ORANGE, '≥66TH')` → `chip(COLOR_GOOD, '≥66TH')`, `chip(BLUE, ...)` → `chip(COLOR_MID, ...)`, `chip(RED, ...)` → `chip(COLOR_WEAK, ...)`.
   - `zone_tile`: `ORANGE` → `COLOR_GOOD`, `RED_TEXT` → `COLOR_WEAK_SOFT`.
   - `factor_rows`: the hardcoded `#C7CDD9` label color → `TEXT_SOFT`.
   - `radar_figure`: `fillcolor="rgba(46,95,183,0.32)"` → `fillcolor=hex_to_rgba(COLOR_PRIMARY, 0.32)`, `line=dict(color=BLUE_TEXT, ...)` → `line=dict(color=COLOR_PRIMARY_SOFT, ...)`, `marker=dict(color=ORANGE, ...)` → `marker=dict(color=COLOR_GOOD, ...)`.
   - `wp_figure`: line `BLUE_TEXT` → `COLOR_PRIMARY_SOFT`, `fillcolor="rgba(46,95,183,0.18)"` → `fillcolor=hex_to_rgba(COLOR_PRIMARY, 0.18)`, end-dot `ORANGE` → `COLOR_GOOD`.
   - `form_figure`: `ORANGE if m > 0 else RED` → `COLOR_GOOD if m > 0 else COLOR_WEAK`.
   - `kpi_card`, `card_title`, `leader_rows`, `stat_tile`: no color-name changes (they use `pctl_*` helpers, `TEXT`, or caller-provided colors).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_overview_cards_colors.py tests/unit/test_overview.py -q`
Expected: PASS (all).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/overview_cards.py tests/unit/test_overview_cards_colors.py
git commit -m "refactor(overview): semantic color tokens and shared Plotly template"
```

---

### Task 8: Overview page migration + Phase A gate

**Files:**
- Modify: `dashboard/app.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 tokens, Task 3 `render_stat_tile_row`, Task 4 `render_page_header`, Task 7 builders.
- Produces: the restyled Overview — reference for every Phase B page migration.

- [ ] **Step 1: Update imports in `dashboard/app.py`**

Replace the `from dashboard.components.theme import (...)` block with:

```python
from dashboard.components.page_header import render_page_header  # noqa: E402
from dashboard.components.stat_tile import render_stat_tile_row  # noqa: E402
from dashboard.components.theme import (  # noqa: E402
    COLOR_GOOD,
    COLOR_PRIMARY,
    COLOR_WEAK,
    COLOR_WEAK_SOFT,
    TEAM_ACCENTS,
    TEXT_FAINT,
    inject_theme,
    render_command_bar,
)
```

(Keep the surrounding import order; ruff will sort.)

- [ ] **Step 2: Swap accent fallback and add the page header**

- Line `accent = TEAM_ACCENTS.get(selected_abbr, ORANGE)` → `accent = TEAM_ACCENTS.get(selected_abbr, COLOR_PRIMARY)`.
- Immediately BEFORE the `st.markdown(cards.team_band(...))` call, add:

```python
render_page_header(
    "Team Overview",
    subtitle=f"{team_name} — every number is real data",
    context_chips=[selected_abbr, season],
)
```

- [ ] **Step 3: Replace the KPI strip with StatTiles**

Replace the whole block from `kpis = st.columns(5)` through the `for col, (label, value, pctl, color) in zip(...)` loop with:

```python
render_stat_tile_row(
    [
        {
            "label": "OFF RATING",
            "value": f"{team_adv['OFF_RATING']:.1f}",
            "pctl": float(team_adv["OFF_RATING_PCTL"]),
        },
        {
            "label": "DEF RATING",
            "value": f"{team_adv['DEF_RATING']:.1f}",
            "pctl": float(team_adv["DEF_RATING_PCTL"]),
        },
        {
            "label": "NET RATING",
            "value": f"{team_adv['NET_RATING']:+.1f}",
            "pctl": float(team_adv["NET_RATING_PCTL"]),
        },
        {
            "label": "PACE",
            "value": f"{team_adv['PACE']:.1f}",
            "pctl": float(team_adv["PACE_PCTL"]),
        },
        {
            "label": "TS%",
            "value": f"{team_adv['TS_PCT'] * 100:.1f}",
            "pctl": float(team_adv["TS_PCT_PCTL"]),
        },
    ]
)
```

- [ ] **Step 4: Fix the remaining hardcoded colors in `app.py`**

- Leaders loop: `("ASSISTS / GM", "AST", "#2E5FB7")` → `("ASSISTS / GM", "AST", COLOR_PRIMARY)`; `("REBOUNDS / GM", "REB", ORANGE)` → `("REBOUNDS / GM", "REB", COLOR_GOOD)`; `("POINTS / GM", "PTS", "#D2243C")` → `("POINTS / GM", "PTS", COLOR_WEAK)`.
- Net-rating small tile: `cards.stat_tile("NET / 100 L10", f"{net100:+.1f}", ORANGE if net100 > 0 else "#E25A6E")` → `cards.stat_tile("NET / 100 L10", f"{net100:+.1f}", COLOR_GOOD if net100 > 0 else COLOR_WEAK_SOFT)`.
- Update the module docstring's first paragraph to name the new language: replace "(orange = good, blue = mid, red = weak)" with "(green = good, yellow = mid, red = weak)".

- [ ] **Step 5: Run the full offline suite**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: PASS; integration tests may SKIP if `data/db/hoops_lab.duckdb` is absent. Zero failures.

- [ ] **Step 6: Boot the real dashboard (repo rule after UI changes)**

```powershell
$p = Start-Process -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList "-m","streamlit","run","dashboard/app.py","--server.headless","true","--server.port","8599" `
  -PassThru
Start-Sleep -Seconds 15
(Invoke-WebRequest -Uri "http://localhost:8599" -UseBasicParsing).StatusCode
Stop-Process -Id $p.Id
```

Expected: `200`. Then eyeball once in a browser against https://worldcup26-analyticslab.vercel.app/ (navy surfaces, blue nav underline, green/yellow/red bars).

- [ ] **Step 7: CHANGELOG entry**

Add at the top of `CHANGELOG.md` (create the file with just this section if missing):

```markdown
## Worldcup26 UI restyle — Phase A (2026-07-24)

- Semantic design tokens (`COLOR_GOOD/MID/WEAK/PRIMARY`) on the Worldcup26 navy palette;
  legacy `ORANGE/BLUE/RED` names alias the new values until Phase B.
- Inter / Inter Tight typography; primary-blue nav and team-rail chrome.
- New components: StatTile, PageHeader, SearchSelect, InfoTooltip.
- Overview migrated to StatTile + PageHeader; shared Plotly template.
```

- [ ] **Step 8: Lint and final commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/app.py CHANGELOG.md
git commit -m "feat(overview): migrate Overview to Worldcup26 StatTile/PageHeader"
```

---

## Phase B (separate plan — do NOT start here)

After the Phase A gate passes, a follow-up plan (`2026-XX-XX-worldcup26-ui-restyle-phase-b.md`) covers: pages 01–09 onto the new components, Plotly template + Altair remap everywhere, alias deletion, legacy `overview_cards.stat_tile`/`kpi_card` removal, and the no-hex-outside-theme grep gate. Per-page edits depend on Phase A's landed API, so they are planned then, not now.
