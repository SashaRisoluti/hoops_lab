"""Tactical alerts panel."""

from __future__ import annotations

import streamlit as st

from hoops_lab.live.alert_engine import Alert


def render_alert_panel(alerts: list[Alert]) -> None:
    """Render alerts by severity; calm reassurance when there are none."""
    st.subheader("🚨 Tactical alerts")
    if not alerts:
        st.success("No tactical alerts right now.")
        return
    for alert in alerts:
        renderer = st.warning if alert.severity == "warning" else st.info
        renderer(f"**{alert.rule.replace('_', ' ')}** — {alert.message}")
