"""Dynamic stats table: column presets, multiselect, sorting, colorscale."""

from __future__ import annotations

import pandas as pd
import streamlit as st

#: Always-visible identity columns.
IDENTITY_COLS = ["PLAYER_NAME", "TEAM_ABBREVIATION", "season"]

#: Quick column presets (spec section 4.2); only columns present in the data
#: are applied.
COLUMN_PRESETS: dict[str, list[str]] = {
    "Box Score": ["GP", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "PF", "PLUS_MINUS"],
    "Shooting": [
        "FGM",
        "FGA",
        "FG_PCT",
        "FG3M",
        "FG3A",
        "FG3_PCT",
        "FTM",
        "FTA",
        "FT_PCT",
        "EFG_PCT",
        "TS_PCT",
    ],
    "Playmaking": ["AST", "AST_PCT", "AST_TO", "AST_RATIO", "TOV", "TM_TOV_PCT"],
    "Advanced Impact": ["OFF_RATING", "DEF_RATING", "NET_RATING", "USG_PCT", "PIE", "PACE", "POSS"],
}

#: Above this many rows the colorscale is skipped (pandas Styler gets slow).
MAX_STYLED_ROWS = 600


def render_stats_table(df: pd.DataFrame) -> list[str]:
    """Render the preset selector, the stat multiselect and the styled table.

    Returns
    -------
    The list of selected stat columns (feeds the percentile histogram).
    """
    preset_name = st.selectbox("Column preset", list(COLUMN_PRESETS))
    numeric_cols = [
        c
        for c in df.columns
        if c not in IDENTITY_COLS and not c.endswith("_ID") and pd.api.types.is_numeric_dtype(df[c])
    ]
    default = [c for c in COLUMN_PRESETS[preset_name] if c in df.columns]
    selected = st.multiselect("Statistics (add or remove columns)", numeric_cols, default=default)

    identity = [c for c in IDENTITY_COLS if c in df.columns]
    view = df[identity + selected]

    if selected and len(view) <= MAX_STYLED_ROWS:
        styled = view.style.background_gradient(subset=selected, cmap="RdYlGn").format(
            precision=2, subset=selected
        )
        st.dataframe(styled, hide_index=True, use_container_width=True)
    else:
        if len(view) > MAX_STYLED_ROWS:
            st.caption(f"Colorscale disabled above {MAX_STYLED_ROWS} rows.")
        st.dataframe(view, hide_index=True, use_container_width=True)

    st.caption("Click a column header to sort; presets can be customised with the multiselect.")
    return selected
