# Worldcup26 UI Restyle — Phase B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Propagate the Worldcup26 design system to all 9 dashboard pages and every chart surface, sync the `hoops_lab/visuals` palette mirror, and delete the Phase A transition scaffolding (aliases, dead builders).

**Architecture:** Pages adopt PageHeader/SearchSelect (they never used legacy aliases — Phase A's alias bridge turned out to be needed only by tests). Chart color debt lives in two Plotly components, four page-level `#888` hlines, and the `hoops_lab/visuals` package, which mirrors tokens by value (layering forbids it importing `dashboard`) and is still on the pre-restyle palette. A `plotly_layout()` factory replaces the mutable `PLOTLY_TEMPLATE` dict. Deletions and permanent gates (no-hex test, mirror-sync test, config-sync test) land last.

**Tech Stack:** Python 3.11, Streamlit, Plotly, Altair, matplotlib (visuals), pytest + AppTest, ruff.

## Global Constraints

- Interpreter: `.venv\Scripts\python.exe`; run everything from the repo root.
- Line length 100 (ruff). After each task: `ruff check --fix . ; ruff format .`
- Type hints on public functions; Google-style docstrings; code in English.
- Hex literals in `dashboard/` live ONLY in `dashboard/components/theme.py`.
- `hoops_lab/` must NEVER import from `dashboard/` (layering). `hoops_lab/visuals/*` mirrors token VALUES as its own constants; Task 8 syncs them and Task 9 locks them with a test.
- Palette (exact): good `#16c47f`, mid `#ffd100`, weak `#e0262c`, primary `#0052ff`, primary-soft `#4d7fff`, weak-soft `#ff5a63`, special `#a855f7`; surfaces `BG_PAGE #070b14`, `BG_CARD #0f172a`, `BG_TILE #141c2e`, `GRID #1c2740`, `COURT_LINE #33415e`; text `#f1f5f9` / soft `#9ca3af` / muted `#64748b`.
- Component APIs (from Phase A, do not change):
  - `render_page_header(title: str, subtitle: str | None = None, context_chips: list[str] | None = None) -> None` (dashboard/components/page_header.py)
  - `search_select(label, options, format_func=str, key=None, index=0, help_text=None) -> T | None` (dashboard/components/search_select.py)
  - `stat_tile_html(label, value, sub=None, delta=None, pctl=None) -> str`, `render_stat_tile_row(tiles: list[dict], columns: int | None = None) -> None` (dashboard/components/stat_tile.py)
  - `info_label_html(label: str, definition: str) -> str` (dashboard/components/info_tooltip.py)
- Page titles drop the emoji when migrating `st.title` → `render_page_header` (Worldcup26 style).
- Unit tests offline; integration tests may SKIP without the local DB, never fail.
- Spec: `docs/superpowers/specs/2026-07-24-worldcup26-ui-restyle-design.md` section 3 Phase B. Scope note (approved intent, records a deviation from the spec's letter): InfoTooltip is adopted where a metric label exists (exemplar on page 01); StatTile is adopted where KPI tiles exist (live KPI strip); not force-fitted onto every page.

---

### Task 1: `plotly_layout()` factory replaces the mutable `PLOTLY_TEMPLATE`

**Files:**
- Modify: `dashboard/components/theme.py:177-183` (the `PLOTLY_TEMPLATE` block)
- Modify: `dashboard/components/overview_cards.py:21,34`
- Modify: `tests/unit/test_theme_tokens.py:15,69-70`

**Interfaces:**
- Produces: `plotly_layout() -> dict` in `theme.py` — returns a FRESH deep copy of the shared Plotly layout kwargs each call. Callers do `fig.update_layout(**plotly_layout(), height=..., ...)`. `PLOTLY_TEMPLATE` is deleted.
- Consumed by: Tasks 3, 4, 5, 6, 7 (every Plotly call site).

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_theme_tokens.py`, replace the import of `PLOTLY_TEMPLATE` with `plotly_layout` and replace `test_plotly_template_uses_inter_on_transparent_paper` with:

```python
def test_plotly_layout_uses_inter_on_transparent_paper() -> None:
    layout = plotly_layout()
    assert "Inter" in layout["font"]["family"]
    assert layout["paper_bgcolor"] == "rgba(0,0,0,0)"


def test_plotly_layout_returns_isolated_copies() -> None:
    first = plotly_layout()
    first["font"]["family"] = "Comic Sans"
    first["margin"]["l"] = 999
    second = plotly_layout()
    assert second["font"]["family"].startswith("Inter")
    assert second["margin"]["l"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_tokens.py -q`
Expected: FAIL — `ImportError: cannot import name 'plotly_layout'`

- [ ] **Step 3: Implement the factory**

In `dashboard/components/theme.py`, add `import copy` next to `import json`, and replace the whole `PLOTLY_TEMPLATE` block (comment + dict, lines 177-183) with:

```python
_PLOTLY_LAYOUT: dict = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=FONT_BODY, color=TEXT),
    margin=dict(l=10, r=10, t=10, b=10),
)


def plotly_layout() -> dict:
    """Fresh copy of the shared Plotly layout kwargs.

    Returns:
        A deep copy — callers may mutate it without affecting other figures.
    """
    return copy.deepcopy(_PLOTLY_LAYOUT)
```

- [ ] **Step 4: Migrate `overview_cards.py`**

- Import line 21: `PLOTLY_TEMPLATE` → `plotly_layout`.
- Line 34: `_PLOTLY_BASE = dict(PLOTLY_TEMPLATE)` → `_PLOTLY_BASE = plotly_layout()`.
(The three `**_PLOTLY_BASE` usages stay — module-level single copy is fine because nothing mutates it; the deepcopy factory removes the shared-nested-dict footgun for new callers.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_theme_tokens.py tests/unit/test_overview_cards_colors.py -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/theme.py dashboard/components/overview_cards.py tests/unit/test_theme_tokens.py
git commit -m "refactor(theme): plotly_layout factory replaces mutable PLOTLY_TEMPLATE"
```

---

### Task 2: StatTile NaN guards for `delta` and `pctl`

**Files:**
- Modify: `dashboard/components/stat_tile.py` (inside `stat_tile_html`)
- Modify: `tests/unit/test_stat_tile.py`

**Interfaces:**
- Produces: `stat_tile_html` silently omits the delta chip when `delta` is NaN and the percentile block when `pctl` is NaN (same as `None`). Signature unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_stat_tile.py`:

```python
def test_nan_delta_and_pctl_are_omitted() -> None:
    html = stat_tile_html("PACE", "99.1", delta=float("nan"), pctl=float("nan"))
    assert "nan" not in html.lower()
    assert "th pctl" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_stat_tile.py::test_nan_delta_and_pctl_are_omitted -q`
Expected: FAIL — rendered HTML contains `+nan` and `nanth pctl`.

- [ ] **Step 3: Implement the guards**

In `stat_tile_html`, change the two condition lines:

```python
    if delta is not None and not math.isnan(delta):
```

```python
    if pctl is not None and not math.isnan(pctl):
```

(`math` is already imported.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_stat_tile.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/stat_tile.py tests/unit/test_stat_tile.py
git commit -m "fix(stat-tile): omit delta and percentile blocks on NaN input"
```

---

### Task 3: Chart components onto tokens — `radar_chart.py`, `percentile_histogram.py`

**Files:**
- Modify: `dashboard/components/radar_chart.py` (hex at :22-23, layout at :27-33)
- Modify: `dashboard/components/percentile_histogram.py` (`crimson` at :41, layout at :45-47)
- Create: `tests/unit/test_chart_components_colors.py`

**Interfaces:**
- Consumes: Task 1 `plotly_layout()`; theme tokens `COLOR_PRIMARY`, `COLOR_PRIMARY_SOFT`, `TEXT`, `hex_to_rgba`.
- Produces: same public signatures — `render_radar_chart(values: dict[str, float], title: str = "") -> None`, `render_percentile_histogram(df, stat_options) -> None`. Both figures now carry the dark template.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_chart_components_colors.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_chart_components_colors.py -q`
Expected: FAIL — spec still contains `#F97316`.
(If the `at.get("plotly_chart")[0].proto.spec` access pattern errors on the installed Streamlit version, adapt the assertion to read the chart's JSON via the element's `.value`/`.figure` attribute — the three color assertions stay identical. Note the change in your report.)

- [ ] **Step 3: Restyle `radar_chart.py`**

Add the import at the top:

```python
from dashboard.components.theme import COLOR_PRIMARY, COLOR_PRIMARY_SOFT, hex_to_rgba, plotly_layout
```

Replace line 22-23:

```python
        line_color=COLOR_PRIMARY_SOFT,
        fillcolor=hex_to_rgba(COLOR_PRIMARY, 0.25),
```

Change the `fig.update_layout(` call (lines 27-33) to spread the template first, keeping every existing kwarg:

```python
    fig.update_layout(
        **plotly_layout(),
        title=title,
        polar=dict(radialaxis=dict(range=[0, 100], showticklabels=True, ticks="")),
        showlegend=False,
        height=430,
    )
```

(If the existing call carries a `margin=` kwarg, DELETE it — `plotly_layout()` already provides `margin` and a duplicate keyword is a runtime `TypeError`.)

- [ ] **Step 4: Restyle `percentile_histogram.py`**

Add the import:

```python
from dashboard.components.theme import COLOR_PRIMARY_SOFT, TEXT, plotly_layout
```

- Line 41: `line_color="crimson"` → `line_color=TEXT` (neutral "you are here" marker on navy).
- After the figure is created, add `fig.update_traces(marker_color=COLOR_PRIMARY_SOFT)` so population bars are soft primary blue.
- The `fig.update_layout(...)` call (lines 45-47): spread `**plotly_layout(),` as the first argument, keep every existing kwarg, delete any duplicate `margin=`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_chart_components_colors.py -q`
Expected: PASS.

- [ ] **Step 6: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/components/radar_chart.py dashboard/components/percentile_histogram.py tests/unit/test_chart_components_colors.py
git commit -m "refactor(charts): radar and histogram onto tokens and shared layout"
```

---

### Task 4: Pages 01 + 02 — PageHeader, SearchSelect, InfoTooltip exemplar, stats-table colormap

**Files:**
- Modify: `dashboard/pages/01_historical_explorer.py` (:24 imports, :30 title, before the `render_percentile_histogram` call)
- Modify: `dashboard/pages/02_player_analyzer.py` (:22 imports, :44 title, :74-78 selectbox)
- Modify: `dashboard/components/stats_table.py:56` (colormap)

**Interfaces:**
- Consumes: `render_page_header`, `search_select`, `info_label_html` (Phase A APIs, signatures in Global Constraints); theme tokens `COLOR_WEAK`, `COLOR_MID`, `COLOR_GOOD`.
- Produces: no new interfaces; pages render the same data with the new chrome.

- [ ] **Step 1: Migrate page 01 header + tooltip exemplar**

In `dashboard/pages/01_historical_explorer.py`:

- Extend imports (line 24 area):

```python
from dashboard.components.info_tooltip import info_label_html
from dashboard.components.page_header import render_page_header
```

- Replace `st.title("📊 Historical Stats Explorer")` (line 30) with:

```python
render_page_header(
    "Historical Stats Explorer",
    subtitle="Filter seasons, teams and stats — percentiles always follow the filtered population",
)
```

- Immediately BEFORE the `render_percentile_histogram(...)` call, add:

```python
st.markdown(
    info_label_html(
        "PERCENTILE",
        "Rank within the filtered population, 0-100. Filters always define the population.",
    ),
    unsafe_allow_html=True,
)
```

- [ ] **Step 2: Migrate the stats-table colormap**

In `dashboard/components/stats_table.py`:

- Add imports at the top:

```python
from matplotlib.colors import LinearSegmentedColormap

from dashboard.components.theme import COLOR_GOOD, COLOR_MID, COLOR_WEAK
```

- Add the module-level constant after the existing constants:

```python
#: weak -> mid -> good, matching the fixed data-color language.
SEMANTIC_CMAP = LinearSegmentedColormap.from_list(
    "hoops_semantic", [COLOR_WEAK, COLOR_MID, COLOR_GOOD]
)
```

- Line 56: `cmap="RdYlGn"` → `cmap=SEMANTIC_CMAP`.

- [ ] **Step 3: Migrate page 02 header + player picker**

In `dashboard/pages/02_player_analyzer.py`:

- Extend imports (line 22 area):

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.search_select import search_select
```

- Replace `st.title("🧬 Player Analyzer")` (line 44) with:

```python
render_page_header("Player Analyzer", subtitle="Percentile profile, advanced stats and on/off impact")
```

- Replace the `st.selectbox("Player", ...)` call (lines 74-78) with a `search_select` call carrying the SAME options and help arguments, e.g.:

```python
    player_name = search_select(
        "Player",
        team_players or population["PLAYER_NAME"].tolist(),
        key="player_pick",
        help_text=<the existing help string, unchanged>,
    )
```

Keep the assigned variable name exactly as it is today (check the original line — the downstream code uses it).

- [ ] **Step 4: Verify**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_dashboard_components.py tests/integration/test_explorer_page.py tests/integration/test_player_page.py -q`
Expected: PASS (integration may SKIP without DB; with the local DB present they must pass).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/pages/01_historical_explorer.py dashboard/pages/02_player_analyzer.py dashboard/components/stats_table.py
git commit -m "feat(pages): explorer and player pages onto PageHeader/SearchSelect"
```

---

### Task 5: Pages 03 + 04 + 05 — PageHeader, SearchSelect, chart template

**Files:**
- Modify: `dashboard/pages/03_team_identity.py` (:20 imports, :43 title, :163-165 figure)
- Modify: `dashboard/pages/04_opponent_scouting.py` (:25 imports, :36 title)
- Modify: `dashboard/pages/05_matchup_analysis.py` (:23 imports, :30 title, :45 selectbox)

**Interfaces:**
- Consumes: `render_page_header`, `search_select`, `plotly_layout()`, `GRID` token.

- [ ] **Step 1: Page 03**

- Imports (line 20 area): add

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.theme import GRID, inject_theme, plotly_layout, render_command_bar
```

(merge with the existing theme import — one import statement, alphabetical.)

- Line 43: `st.title("🛡️ Team Identity")` →

```python
render_page_header("Team Identity", subtitle="Ratings, Four Factors and playmaking trends")
```

- Line 164: `fig.add_hline(y=0, line_dash="dot", line_color="#888")` → `line_color=GRID`.
- Line 165: `fig.update_layout(height=320, xaxis_title="", yaxis_title="Avg +/- (last 5)")` →

```python
fig.update_layout(**plotly_layout(), height=320, xaxis_title="", yaxis_title="Avg +/- (last 5)")
```

- [ ] **Step 2: Page 04**

- Imports (line 25 area): add `from dashboard.components.page_header import render_page_header`.
- Line 36: `st.title("🔎 Opponent Scouting")` →

```python
render_page_header("Opponent Scouting", subtitle="Identity, strengths and shot archetypes of the next opponent")
```

- [ ] **Step 3: Page 05**

- Imports (line 23 area): add

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.search_select import search_select
```

- Line 30: `st.title("⚔️ Matchup Analysis")` →

```python
render_page_header("Matchup Analysis", subtitle="Side-by-side Four Factors and leverage")
```

- Line 45: `opponent = st.sidebar.selectbox("Opponent", opponent_options)` →

```python
with st.sidebar:
    opponent = search_select("Opponent", opponent_options, key="matchup_opponent")
```

(Keep the variable name `opponent` — verify against the original line's actual variable name and keep it identical.)

- [ ] **Step 4: Verify**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_phase3_pages.py tests/unit/test_team_identity.py tests/unit/test_matchup_scouting.py -q`
Expected: PASS (integration may SKIP without DB).

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/pages/03_team_identity.py dashboard/pages/04_opponent_scouting.py dashboard/pages/05_matchup_analysis.py
git commit -m "feat(pages): identity, scouting and matchup onto PageHeader/SearchSelect"
```

---

### Task 6: Pages 06 + 07 — PageHeader, semantic scatter scale

**Files:**
- Modify: `dashboard/pages/06_shot_map.py` (:22 imports, :28 title)
- Modify: `dashboard/pages/07_lineup_explorer.py` (:24 imports, :46 title, :99-111 figure)

**Interfaces:**
- Consumes: `render_page_header`, `plotly_layout()`, tokens `GRID`, `COLOR_WEAK`, `COLOR_MID`, `COLOR_GOOD`.

- [ ] **Step 1: Page 06**

- Imports (line 22 area): add `from dashboard.components.page_header import render_page_header`.
- Line 28: `st.title("🎯 Shot Map")` →

```python
render_page_header("Shot Map", subtitle="Half-court locations and zone efficiency")
```

(The multiselect at :52 stays a multiselect — `search_select` is single-select by design.)

- [ ] **Step 2: Page 07**

- Imports (line 24 area): add

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.theme import (
    COLOR_GOOD,
    COLOR_MID,
    COLOR_WEAK,
    GRID,
    inject_theme,
    plotly_layout,
    render_command_bar,
)
```

(one merged theme import.)

- Line 46: `st.title("🧩 Lineup Explorer")` →

```python
render_page_header("Lineup Explorer", subtitle="Five-man units — complete population, minimum-sample filtered")
```

- In the `px.scatter(...)` call (lines 99-107): `color_continuous_scale="RdYlGn"` →

```python
color_continuous_scale=[(0.0, COLOR_WEAK), (0.5, COLOR_MID), (1.0, COLOR_GOOD)],
```

- Line 108: `line_color="#888"` → `line_color=GRID`.
- Lines 109-111: prepend the template to the existing kwargs:

```python
fig.update_layout(**plotly_layout(), height=420, xaxis_title=..., yaxis_title=...)
```

(keep the existing title strings verbatim; delete any duplicate `margin=`.)

- [ ] **Step 3: Verify**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_shot_zone.py tests/unit/test_lineup_explorer.py -q`
Expected: PASS.

- [ ] **Step 4: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/pages/06_shot_map.py dashboard/pages/07_lineup_explorer.py
git commit -m "feat(pages): shot map and lineups onto PageHeader, semantic scatter scale"
```

---

### Task 7: Pages 08 + 09 — PageHeader, SearchSelect game pickers, StatTile KPI strip

**Files:**
- Modify: `dashboard/pages/08_live_command_center.py` (:25 imports, :40 title, :85 + :122 selectboxes, :192-197 figure)
- Modify: `dashboard/pages/09_post_game_review.py` (:23 imports, :44 title, :72 selectbox, :140-145 figure)
- Modify: `dashboard/components/live_kpi_strip.py` (metric row → StatTiles)
- Modify: `tests/unit/test_game_state.py` / live-strip tests ONLY if they assert on `st.metric` elements (check first; adapt assertions, do not delete tests)

**Interfaces:**
- Consumes: `render_page_header`, `search_select`, `stat_tile_html`, `plotly_layout()`, `GRID`.
- Produces: `render_kpi_strip(state, home_label, away_label) -> None` — signature unchanged, renders StatTiles instead of `st.metric`.

- [ ] **Step 1: Page 08**

- Imports (line 25 area): add

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.search_select import search_select
from dashboard.components.theme import GRID, inject_theme, plotly_layout, render_command_bar
```

(one merged theme import.)

- Line 40: `st.title("📡 Live Command Center")` →

```python
render_page_header("Live Command Center", subtitle="Live KPIs, alerts and win probability")
```

- Line 85: `chosen = st.selectbox("Live game", list(labels))` →

```python
chosen = search_select("Live game", list(labels), key="live_game_pick")
```

- Line 122: `chosen = st.sidebar.selectbox("Game", labels)` →

```python
with st.sidebar:
    chosen = search_select("Game", labels, key="replay_game_pick")
```

- Line 192: `line_color="#888"` → `line_color=GRID`.
- Lines 193-197: prepend `**plotly_layout(),` to the existing `fig.update_layout(...)` kwargs (keep them verbatim, delete any duplicate `margin=`).

- [ ] **Step 2: Page 09**

- Imports (line 23 area): add

```python
from dashboard.components.page_header import render_page_header
from dashboard.components.search_select import search_select
from dashboard.components.theme import GRID, inject_theme, plotly_layout, render_command_bar
```

- Line 44: `st.title("📝 Post-Game Review")` →

```python
render_page_header("Post-Game Review", subtitle="Full-game story: score, factors and win probability")
```

- Line 72: `st.sidebar.selectbox("Game (📊 = play-by-play available)", labels)` →

```python
with st.sidebar:
    chosen = search_select("Game (📊 = play-by-play available)", labels, key="review_game_pick")
```

(Keep the exact variable name from the original line.)

- Line 140: `line_color="#888"` → `line_color=GRID`.
- Lines 141-145: prepend `**plotly_layout(),` to the existing kwargs.

- [ ] **Step 3: Live KPI strip onto StatTiles**

Read `dashboard/components/live_kpi_strip.py` (42 lines). Transformation, exact:

- Add import: `from dashboard.components.stat_tile import stat_tile_html`.
- Every `col.metric(<label>, <value>)` / `st.metric(...)` call inside `render_kpi_strip` becomes:

```python
col.markdown(stat_tile_html(<label>, <value>), unsafe_allow_html=True)
```

with the SAME label and value expressions. If a metric call passes `delta=<expr>`, carry it: `stat_tile_html(<label>, <value>, delta=<expr>)` (delta must be a float — cast if the current code formats it as a string, and note it in your report). The score header and `_pretty_clock` stay untouched. Signature `render_kpi_strip(state: GameState, home_label: str, away_label: str) -> None` unchanged.

- [ ] **Step 4: Verify**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_game_state.py tests/unit/test_alert_engine.py tests/integration/test_phase5.py -q`
Expected: PASS (integration may SKIP). If a unit test asserted on `st.metric` elements of the strip, update it to assert the tile HTML (label string present in markdown) instead — never delete the test.

- [ ] **Step 5: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add dashboard/pages/08_live_command_center.py dashboard/pages/09_post_game_review.py dashboard/components/live_kpi_strip.py tests/
git commit -m "feat(pages): live and post-game onto PageHeader/SearchSelect/StatTile strip"
```

---

### Task 8: `hoops_lab/visuals` palette mirror sync

**Files:**
- Modify: `hoops_lab/visuals/altair_charts.py` (:7-8 docstring, :18-24 constants, :27-28, :72, :138, :174, :179, :203, :260, :312)
- Modify: `hoops_lab/visuals/court.py` (:19-20)
- Modify: `hoops_lab/visuals/heatmaps.py` (:20, :22-24, :34, :81, :174-175, :177, :218)
- Modify: `hoops_lab/visuals/shot_maps.py` (:15-17, :98 and other `#EDEFF3` sites)
- Modify: `tests/unit/test_altair_charts.py`, `tests/unit/test_court_visuals.py`, `tests/unit/test_shot_som.py` — ONLY where they pin old hex values (check first)

**Interfaces:**
- Produces: same public functions; module constants renamed/revalued. NO import from `dashboard` — layering rule. New constant names in `altair_charts.py`: `COLOR_GOOD "#16c47f"`, `COLOR_MID "#ffd100"`, `COLOR_WEAK "#e0262c"` (replacing `ORANGE`/`BLUE`/`RED`), surfaces `BG_CARD "#0f172a"`, `GRID "#1c2740"`, `TEXT "#f1f5f9"`, `TEXT_MUTED "#9ca3af"`.
- Consumed by: Task 9's mirror-sync test.

- [ ] **Step 1: `altair_charts.py`**

- Docstring lines 7-8: "orange = good, blue = mid, red = weak" → "green = good, yellow = mid, red = weak".
- Constants block lines 18-24 becomes:

```python
BG_CARD = "#0f172a"
GRID = "#1c2740"
TEXT = "#f1f5f9"
TEXT_MUTED = "#9ca3af"
COLOR_GOOD = "#16c47f"
COLOR_MID = "#ffd100"
COLOR_WEAK = "#e0262c"
```

(Comment above it stays "Mirrors of the dashboard design tokens" — Task 9 locks the mirror with a test.)

- Every use-site rename, exact:
  - :28 `TRICOLOR_RANGE = [ORANGE, BLUE, RED]` → `[COLOR_GOOD, COLOR_MID, COLOR_WEAK]`
  - :72 `range=[ORANGE, BLUE]` → `range=[COLOR_GOOD, COLOR_MID]`
  - :138 `mark_line(color=ORANGE, point=alt.OverlayMarkDef(color=ORANGE, size=24))` → both `COLOR_GOOD`
  - :174 `range=[RED, BLUE, ORANGE]` → `range=[COLOR_WEAK, COLOR_MID, COLOR_GOOD]` (fixes the order-inconsistency: weak→mid→good everywhere)
  - :179 `alt.value(BLUE)` → `alt.value(COLOR_MID)`
  - :203 `mark_bar(color=ORANGE)` → `mark_bar(color=COLOR_GOOD)`
  - :260 `alt.value(BLUE)` → `alt.value(COLOR_MID)`
  - :312 `alt.value(ORANGE), alt.value(RED)` → `alt.value(COLOR_GOOD), alt.value(COLOR_WEAK)`

- [ ] **Step 2: `court.py`**

Lines 19-20:

```python
COURT_BG = "#0f172a"
COURT_LINE = "#33415e"
```

- [ ] **Step 3: `heatmaps.py`**

- :20 density ramp `[COURT_BG, "#2E5FB7", "#F0703A"]` → `[COURT_BG, "#0052ff", "#ffd100"]` (cold navy → primary blue → hot yellow).
- :22-24 efficiency ramp `["#D2243C", "#2E5FB7", "#F0703A"]` → `["#e0262c", "#ffd100", "#16c47f"]` (weak → mid → good).
- Text colors: every `"#8B93A3"` (:34, :174, :175) → `"#9ca3af"`; every `"#EDEFF3"` (:81, :177, :218) → `"#f1f5f9"`.

- [ ] **Step 4: `shot_maps.py`**

- :15 `MADE_COLOR = "#F0703A"` → `"#16c47f"`
- :16 `MISS_COLOR = "#D2243C"` → `"#e0262c"`
- :17 `TEXT_MUTED = "#8B93A3"` → `"#9ca3af"`
- Every `"#EDEFF3"` literal (title colors, :98 etc.) → `"#f1f5f9"`.

- [ ] **Step 5: Verify (and fix pinned-hex tests)**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_altair_charts.py tests/unit/test_court_visuals.py tests/unit/test_shot_som.py tests/unit/test_shot_archetypes.py -q`
If a test pinned an OLD hex (e.g. asserted `#F0703A` in a chart spec), update the assertion to the new palette value — the test's structure stays, only the expected color changes. List every such change in the report.
Expected after updates: PASS.

- [ ] **Step 6: Lint and commit**

```bash
ruff check --fix . && ruff format .
git add hoops_lab/visuals/ tests/
git commit -m "feat(visuals): sync hoops_lab palette mirror to Worldcup26 tokens"
```

---

### Task 9: Deletions + permanent gates + Phase B close

**Files:**
- Modify: `dashboard/components/theme.py:43-47` (delete aliases)
- Modify: `dashboard/components/overview_cards.py` (:47 delete `kpi_card`, :192 rename `stat_tile` → `mini_tile`)
- Modify: `dashboard/app.py:317-323` (rename call sites)
- Modify: `tests/unit/test_theme_tokens.py` (drop alias test)
- Create: `tests/unit/test_design_gates.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `overview_cards.mini_tile(label: str, value: str, color: str = TEXT) -> str` (body identical to the old small `stat_tile` — rename only, kills the name collision with the StatTile module). `ORANGE/BLUE/BLUE_TEXT/RED/RED_TEXT` and `kpi_card` cease to exist.

- [ ] **Step 1: Write the failing gate tests**

Create `tests/unit/test_design_gates.py`:

```python
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
```

- [ ] **Step 2: Run gates to verify current failures**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_design_gates.py -q`
Expected: `test_legacy_names_are_gone` FAILS (aliases + kpi_card + stat_tile still exist). The other three should already PASS after Tasks 3-8 — if `test_no_hex_literals_in_dashboard_outside_theme` fails, its offender list is your remaining worklist; fix those sites with tokens before continuing.

- [ ] **Step 3: Deletions and rename**

- `theme.py`: delete the whole aliases block (lines 43-47 and its `# ---- Legacy aliases` comment).
- `overview_cards.py`: delete the `kpi_card` function (line 47, whole body); rename `def stat_tile(` (line 192) to `def mini_tile(` (docstring stays).
- `dashboard/app.py` lines 317-323: `cards.stat_tile(` → `cards.mini_tile(` (3 call sites).
- `tests/unit/test_theme_tokens.py`: delete `test_legacy_aliases_point_at_new_tokens` and remove `ORANGE`, `BLUE`, `RED` from the import.

- [ ] **Step 4: Full suite**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: PASS, zero failures (integration may SKIP without DB).

- [ ] **Step 5: Boot check (repo rule after UI changes)**

```powershell
$p = Start-Process -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList "-m","streamlit","run","dashboard/app.py","--server.headless","true","--server.port","8599" `
  -PassThru
Start-Sleep -Seconds 15
(Invoke-WebRequest -Uri "http://localhost:8599" -UseBasicParsing).StatusCode
Stop-Process -Id $p.Id
```

Expected: `200`.

- [ ] **Step 6: CHANGELOG entry**

Add at the top of `CHANGELOG.md`:

```markdown
## Worldcup26 UI restyle — Phase B (2026-07-24)

- All 9 pages migrated to PageHeader; searchable pickers (player, opponent, games) via SearchSelect.
- Every Plotly surface on the shared `plotly_layout()` template; semantic weak/mid/good scales
  replace RdYlGn; `hoops_lab/visuals` palette mirror synced to the Worldcup26 tokens.
- Live KPI strip renders StatTiles; NaN guards on StatTile delta/percentile.
- Legacy aliases (`ORANGE/BLUE/RED/...`), `kpi_card` deleted; small tile renamed `mini_tile`.
- Permanent gates: no-hex-outside-theme, visuals-mirror sync, config.toml/token sync.
```

- [ ] **Step 7: Lint and final commit**

```bash
ruff check --fix . && ruff format .
git add -A
git commit -m "feat(ui): Phase B close — deletions, design gates, CHANGELOG"
```

---

## Notes for the controller

- Tasks 1-3 are prerequisites for 4-7 (factory + guards + chart components). Tasks 4-7 (pages) are mutually independent but must run SEQUENTIALLY (same repo, commit ordering). Task 8 is independent of 4-7. Task 9 must be last.
- Inventory provenance: line numbers come from a read-only sweep at commit `ef4c8fc`; if a file drifted, the implementer matches on the quoted code, not the line number.
- The visual eyeball check against https://worldcup26-analyticslab.vercel.app/ remains manual after Task 9.
