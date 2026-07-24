"""HTML/Plotly builders for the Overview dashboard (design handoff v2)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

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
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    TEXT_SOFT,
    hex_to_rgba,
    pctl_color,
    plotly_layout,
)

_CARD = f"background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:14px 16px 12px;"
_EYEBROW = f"font-family:{FONT_MONO};font-size:10px;letter-spacing:0.12em;color:{TEXT_MUTED};"

_PLOTLY_BASE = plotly_layout()


def card_title(title: str, right: str = "") -> str:
    """Uppercase condensed card heading with an optional mono right label."""
    return (
        '<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'<span style="font-family:{FONT_DISPLAY};font-size:17px;font-weight:600;'
        f'letter-spacing:0.05em;text-transform:uppercase;color:{TEXT};">{title}</span>'
        f'<span style="{_EYEBROW}">{right}</span></div>'
    )


def team_band(
    accent: str,
    name: str,
    subtitle: str,
    last5: list[str],
    last_game: str,
    abbr: str,
    logo: str | None = None,
) -> str:
    """Team identity band: accent stripe + gradient, logo ring, last-5 chips."""
    chips = ""
    for result in last5:
        won = result == "W"
        color, bg = (
            (COLOR_GOOD, hex_to_rgba(COLOR_GOOD, 0.18))
            if won
            else (COLOR_WEAK_SOFT, hex_to_rgba(COLOR_WEAK, 0.14))
        )
        border = COLOR_GOOD if won else COLOR_WEAK
        chips += (
            f'<div style="width:24px;height:24px;border-radius:6px;background:{bg};'
            f"border:1px solid {border};color:{color};font-size:11px;font-weight:700;"
            f'display:flex;align-items:center;justify-content:center;">{result}</div>'
        )
    badge = (
        f'<img src="{logo}" alt="{abbr}" style="width:40px;height:40px;">'
        if logo
        else f'<span style="font-family:{FONT_MONO};font-size:14px;font-weight:700;color:{accent};">{abbr}</span>'
    )
    return f"""<div style="display:flex;align-items:center;gap:22px;padding:20px 24px;
  border:1px solid {BORDER};border-radius:10px;
  background:linear-gradient(90deg,{hex_to_rgba(accent, 0.16)},rgba(0,0,0,0) 55%),{BG_CARD};
  box-shadow:inset 0 3px 0 {accent};">
  <div style="width:58px;height:58px;border-radius:50%;border:2px solid {accent};background:{BG_TILE};
    display:flex;align-items:center;justify-content:center;">{badge}</div>
  <div>
    <div style="font-family:{FONT_DISPLAY};font-size:32px;font-weight:700;letter-spacing:0.05em;line-height:1;color:{TEXT};">{name.upper()}</div>
    <div style="font-size:13px;color:{TEXT_MUTED};font-weight:500;">{subtitle}</div>
  </div>
  <div style="flex:1;"></div>
  <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;">
    <div style="{_EYEBROW}">LAST 5</div>
    <div style="display:flex;gap:5px;">{chips}</div>
  </div>
  <div style="width:1px;height:44px;background:{BORDER};"></div>
  <div style="display:flex;flex-direction:column;gap:2px;align-items:flex-end;">
    <div style="{_EYEBROW}">LAST GAME</div>
    <div style="font-size:14px;font-weight:600;color:{TEXT};">{last_game}</div>
  </div>
</div>"""


def flag_box(severity: str, message: str) -> str:
    """Tactical flag row (HIGH red / MED yellow / LOW blue)."""
    palette = {
        "HIGH": (COLOR_WEAK, COLOR_WEAK_SOFT, 0.10, 0.45),
        "MED": (COLOR_MID, COLOR_MID, 0.08, 0.40),
        "LOW": (COLOR_PRIMARY, COLOR_PRIMARY_SOFT, 0.08, 0.40),
    }
    base, text_color, bg_a, border_a = palette.get(severity, palette["LOW"])
    return (
        f'<div style="display:flex;align-items:center;gap:10px;background:{hex_to_rgba(base, bg_a)};'
        f'border:1px solid {hex_to_rgba(base, border_a)};border-radius:8px;padding:10px 12px;margin-bottom:8px;">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{base};flex-shrink:0;"></span>'
        f'<div style="font-size:12.5px;line-height:1.35;color:{TEXT};">'
        f'<strong style="color:{text_color};">{severity}</strong> — {message}</div></div>'
    )


def leader_rows(rows: list[tuple[str, float]], color: str) -> str:
    """Top-3 leader bars, widths relative to the category leader."""
    top = max((value for _, value in rows), default=1.0) or 1.0
    html = ""
    for name, value in rows:
        html += (
            '<div style="display:grid;grid-template-columns:1fr 44px 100px;gap:10px;'
            'align-items:center;font-size:12.5px;margin-bottom:7px;">'
            f'<div style="font-weight:600;color:{TEXT};">{name}</div>'
            f'<div style="text-align:right;font-weight:600;color:{TEXT};">{value:.1f}</div>'
            f'<div style="height:5px;border-radius:3px;background:{BORDER};">'
            f'<div style="width:{value / top * 100:.0f}%;height:100%;background:{color};border-radius:3px;"></div>'
            "</div></div>"
        )
    return html


def factor_rows(rows: list[tuple[str, str, float]]) -> str:
    """Four Factors detail rows: label, value, tricolor pctl bar, pctl."""
    html = ""
    for label, value, pctl in rows:
        html += (
            '<div style="display:grid;grid-template-columns:86px 52px 1fr 28px;gap:8px;'
            'align-items:center;font-size:12px;margin-bottom:6px;">'
            f'<div style="color:{TEXT_SOFT};">{label}</div>'
            f'<div style="font-weight:600;text-align:right;color:{TEXT};">{value}</div>'
            f'<div style="height:5px;border-radius:3px;background:{BORDER};overflow:hidden;">'
            f'<div style="width:{pctl:.0f}%;height:100%;background:{pctl_color(pctl)};border-radius:3px;"></div></div>'
            f'<div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_MUTED};text-align:right;">{pctl:.0f}</div>'
            "</div>"
        )
    return html


def tricolor_legend() -> str:
    """The fixed data-color legend (>=66 / 33-66 / <33)."""

    def chip(color: str, label: str) -> str:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;">'
            f'<span style="width:8px;height:5px;border-radius:2px;background:{color};"></span>{label}</span>'
        )

    return (
        f'<div style="font-size:10px;font-family:{FONT_MONO};color:{TEXT_FAINT};margin-top:4px;">'
        f"{chip(COLOR_GOOD, '≥66TH')}{chip(COLOR_MID, '33–66TH')}{chip(COLOR_WEAK, '&lt;33RD')}</div>"
    )


def zone_tile(label: str, fg_pct: float, is_three: bool) -> str:
    """Zone efficiency tile, value colored by sensible FG% thresholds."""
    good, bad = (0.38, 0.33) if is_three else (0.58, 0.45)
    color = COLOR_GOOD if fg_pct >= good else (COLOR_WEAK_SOFT if fg_pct < bad else TEXT)
    return (
        f'<div style="background:{BG_TILE};border:1px solid {BORDER};border-radius:7px;'
        'padding:8px 10px;text-align:center;">'
        f'<div style="{_EYEBROW}font-size:9px;">{label}</div>'
        f'<div style="font-family:{FONT_DISPLAY};font-size:22px;font-weight:700;color:{color};">{fg_pct:.0%}</div>'
        "</div>"
    )


def mini_tile(label: str, value: str, color: str = TEXT) -> str:
    """Small mono-label stat tile (NET RTG L10 / HOME / ROAD)."""
    return (
        f'<div style="background:{BG_TILE};border:1px solid {BORDER};border-radius:7px;'
        'padding:8px 10px;text-align:center;">'
        f'<div style="{_EYEBROW}font-size:9px;">{label}</div>'
        f'<div style="font-family:{FONT_DISPLAY};font-size:22px;font-weight:700;color:{color};">{value}</div>'
        "</div>"
    )


def radar_figure(values: dict[str, float]) -> go.Figure:
    """Eight-axis percentile radar in the design palette."""
    categories = list(values)
    radii = [values[c] for c in categories]
    fig = go.Figure(
        go.Scatterpolar(
            r=radii + radii[:1],
            theta=categories + categories[:1],
            fill="toself",
            fillcolor=hex_to_rgba(COLOR_PRIMARY, 0.32),
            line=dict(color=COLOR_PRIMARY_SOFT, width=2),
            marker=dict(color=COLOR_GOOD, size=7),
            hovertemplate="%{theta}: %{r:.0f}th pctl<extra></extra>",
        )
    )
    fig.update_layout(
        **_PLOTLY_BASE,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 100],
                tickvals=[33, 66, 100],
                gridcolor=GRID,
                tickfont=dict(size=9, color=TEXT_MUTED),
            ),
            angularaxis=dict(gridcolor=GRID, tickfont=dict(size=10, color=TEXT_MUTED)),
        ),
        showlegend=False,
        height=330,
    )
    return fig


def wp_figure(curve: pd.DataFrame) -> go.Figure:
    """Win probability line: blue with gradient fill and a green end dot."""
    y = curve["wp_home"].reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=y,
            mode="lines",
            line=dict(color=COLOR_PRIMARY_SOFT, width=2.5),
            fill="tozeroy",
            fillcolor=hex_to_rgba(COLOR_PRIMARY, 0.18),
            hovertemplate="%{y:.0%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[len(y) - 1],
            y=[y.iloc[-1]],
            mode="markers",
            marker=dict(color=COLOR_GOOD, size=9),
            hoverinfo="skip",
        )
    )
    fig.add_hline(y=0.5, line_dash="dot", line_color=GRID)
    fig.update_layout(
        **_PLOTLY_BASE,
        height=170,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(
            range=[0, 1], tickformat=".0%", gridcolor=GRID, tickfont=dict(size=9, color=TEXT_MUTED)
        ),
    )
    return fig


def form_figure(games: pd.DataFrame) -> go.Figure:
    """Last-10 diverging margin bars: wins up in green, losses down in red."""
    margins = games["PLUS_MINUS"].astype(float).tolist()
    labels = [
        f"{'@' if not home else ''}{opp} {margin:+.0f}"
        for home, opp, margin in zip(
            games["is_home"], games["OPP_ABBREVIATION"], margins, strict=True
        )
    ]
    colors = [COLOR_GOOD if m > 0 else COLOR_WEAK for m in margins]
    positions = list(range(len(margins)))  # explicit ticks: labels can repeat
    fig = go.Figure(
        go.Bar(
            x=positions,
            y=margins,
            marker_color=colors,
            customdata=labels,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color=GRID)
    fig.update_layout(
        **_PLOTLY_BASE,
        height=210,
        showlegend=False,
        xaxis=dict(
            tickmode="array",
            tickvals=positions,
            ticktext=labels,
            tickfont=dict(size=9, color=TEXT_FAINT),
        ),
        yaxis=dict(gridcolor=GRID, tickfont=dict(size=9, color=TEXT_MUTED)),
        bargap=0.25,
    )
    return fig
