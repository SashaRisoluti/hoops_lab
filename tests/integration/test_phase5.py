"""Phase 5 integration: the Live Command Center page in replay mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_live_command_center_replay_renders() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/08_live_command_center.py", default_timeout=120)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    # Live KPI strip renders StatTile HTML via st.markdown, not st.metric.
    strip_html = "".join(m.value for m in at.markdown)
    assert "eFG%" in strip_html, "live KPI strip missing"
    assert "PPP" in strip_html, "live KPI strip missing"
    assert len(at.dataframe) >= 1, "timeline / comparison tables missing"
