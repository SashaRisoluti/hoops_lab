## Worldcup26 UI restyle — Phase B (2026-07-24)

- All 9 pages migrated to PageHeader; searchable pickers (player, opponent, games) via SearchSelect.
- Every Plotly surface on the shared `plotly_layout()` template; semantic weak/mid/good scales
  replace RdYlGn; `hoops_lab/visuals` palette mirror synced to the Worldcup26 tokens.
- Live KPI strip renders StatTiles; NaN guards on StatTile delta/percentile.
- Legacy aliases (`ORANGE/BLUE/RED/...`), `kpi_card` deleted; small tile renamed `mini_tile`.
- Permanent gates: no-hex-outside-theme, visuals-mirror sync, config.toml/token sync.

## Worldcup26 UI restyle — Phase A (2026-07-24)

- Semantic design tokens (`COLOR_GOOD/MID/WEAK/PRIMARY`) on the Worldcup26 navy palette;
  legacy `ORANGE/BLUE/RED` names alias the new values until Phase B.
- Inter / Inter Tight typography; primary-blue nav and team-rail chrome.
- New components: StatTile, PageHeader, SearchSelect, InfoTooltip.
- Overview migrated to StatTile + PageHeader; shared Plotly template.
