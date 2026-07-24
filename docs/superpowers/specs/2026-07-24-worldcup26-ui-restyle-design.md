# Worldcup26 UI Restyle — Design Spec

Date: 2026-07-24
Status: approved (brainstorming session)
Reference: https://worldcup26-analyticslab.vercel.app/ (Vite + React + Tailwind SPA)

## Goal

Restyle the hoops-lab Streamlit dashboard to match the visual language of the Worldcup26
Analytics Lab: deep navy surfaces, Inter typography, green/yellow/red data semantics,
electric-blue primary, and a reusable component system (StatTile, PageHeader, SearchSelect,
InfoTooltip). The stack stays Streamlit; a React SPA migration is documented as a future
path only (section 6).

## Decisions made

| Decision | Choice |
|---|---|
| Depth | Restyle Streamlit now; React SPA documented as future plan |
| Palette | Full Worldcup26 adoption, including data-color semantics remap |
| Rollout | Phased: core + Overview first (Phase A), remaining pages after (Phase B) |
| UX patterns | Component system only — no new pages, no comparison-page rework |
| Architecture | In-place token swap in `theme.py` with semantic token names |

## 1. Design tokens (`dashboard/components/theme.py` rewrite)

Reference values extracted from the deployed Worldcup26 CSS bundle.

### Surfaces

| Token | Value | Use |
|---|---|---|
| `BG_PAGE` | `#070b14` | page background |
| `BG_FRAME` | `#0b0f19` | frame / shell background |
| `BG_CARD` | `#0f172a` | cards |
| `BG_TILE` | `#141c2e` | stat tiles, nested surfaces |
| `BORDER` | `#111829` | card borders |
| `BORDER_SOFT` | `#0e1320` | subtle separators |

### Data semantics (renamed from ORANGE/BLUE/RED)

| Token | Value | Meaning |
|---|---|---|
| `COLOR_GOOD` | `#16c47f` | ≥66th percentile |
| `COLOR_MID` | `#ffd100` | 33rd–66th percentile |
| `COLOR_WEAK` | `#e0262c` | <33rd percentile |
| `COLOR_PRIMARY` | `#0052ff` | selection, nav active, interactive elements |
| `COLOR_SPECIAL` | `#a855f7` | model/AI-derived flags (archetypes, predictions) |

### Text

`TEXT #f1f5f9`, `TEXT_SOFT #9ca3af`, `TEXT_MUTED #64748b`.

### Typography

Inter 400–900 (body), Inter Tight 700–900 (display/headers), `ui-monospace` for
tricodes and KPI numerals. Loaded from Google Fonts with the same pattern used today.

### Rules

- `pctl_color()` keeps its 33/66 thresholds and remaps to `COLOR_WEAK`/`COLOR_MID`/`COLOR_GOOD`.
- `TEAM_ACCENTS` (30 NBA franchise colors) is unchanged — team identity styling stays.
- Legacy token names (`ORANGE`, `BLUE`, `RED`, …) become aliases of the new tokens during
  Phase A so unmigrated pages instantly render the new palette; aliases are deleted at the
  end of Phase B.
- A `TOKENS` dict plus a JSON export helper make the token set portable (React port seed).
- `.streamlit/config.toml`: `primaryColor #0052ff`, `backgroundColor #070b14`,
  `secondaryBackgroundColor #0f172a`, `textColor #f1f5f9`.

## 2. Component system (new files in `dashboard/components/`)

All components follow the repo contract: pure render, receive data as arguments,
return `None`, never call the database.

| File | API | Purpose |
|---|---|---|
| `stat_tile.py` | `stat_tile(label, value, sub=None, delta=None, pctl=None)`, `stat_tile_row(tiles)` | Worldcup26-style stat tiles; replaces `kpi_card` |
| `page_header.py` | `page_header(title, subtitle=None, context_chips=None)` | Consistent Inter Tight display header on every page |
| `search_select.py` | standardized searchable team/player picker (wraps `st.selectbox`, logo formatting) | one selection UX everywhere |
| `info_tooltip.py` | metric-definition tooltips attached to stat labels | metric literacy |

Also: `overview_cards.py` refactored onto the new tokens, and a shared Plotly template
object declared once in `theme.py` so every figure inherits fonts/surfaces/gridlines.

## 3. Rollout

**Phase A — core + Overview**
1. `theme.py` token rewrite (+ aliases) and `.streamlit/config.toml`.
2. Four new components.
3. Command bar + team rail restyle.
4. `dashboard/app.py` (Overview) migrated to StatTile/PageHeader.

**Phase B — propagation**
1. Pages `01`–`09` migrated to StatTile/PageHeader/SearchSelect/InfoTooltip.
2. Plotly template applied to all figures; Altair archetype charts remapped.
3. Legacy aliases removed.
4. Final sweep: no hex literals outside `theme.py`.

Each phase lands as separate commits with a CHANGELOG entry.

## 4. Verification gates

Per phase:
- Existing AppTest suite green.
- Headless `streamlit run` boots + HTTP check (repo rule after UI changes).
- Visual check against the reference site.

New unit tests:
- `pctl_color` threshold mapping at the 33/66 boundaries.
- StatTile/PageHeader render smoke via AppTest.

Phase B adds a grep-based check that no hardcoded hex colors exist outside `theme.py`.

## 5. Error handling

Components render graceful placeholders on missing data (`None`/NaN → em-dash in tiles),
matching current dashboard behavior. No new failure modes are introduced — components are
pure functions over already-fetched data.

## 6. Future React SPA migration (documented only — no code in this project)

| Streamlit piece | React equivalent (Worldcup26 naming) |
|---|---|
| `stat_tile.py` | `StatTile` |
| `page_header.py` | `PageHeader` |
| `search_select.py` | `SearchSelect` |
| `team_rail.py` | `TeamFlag` rail |
| command bar | `AppShell` |
| `TOKENS` JSON | Tailwind config seed |
| `hoops_lab/` package | unchanged backend |
| `api/` FastAPI stub | data layer (already planned as Fase 4+ stack) |

The token JSON export and the pure-render component contract are the two design choices
made specifically to keep this port cheap.
