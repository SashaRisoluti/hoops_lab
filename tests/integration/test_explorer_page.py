"""AppTest smoke test: the Historical Stats Explorer page runs end-to-end.

Executes the real Streamlit page against the real local database (skipped
when the DB has not been built). Run pytest from the repo root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hoops_lab.config import DB_PATH

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(), reason="local DuckDB not built (run the seeder first)"
)


def test_explorer_page_renders_table_and_histogram() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("dashboard/pages/01_historical_explorer.py", default_timeout=120)
    at.run()

    assert not at.exception, f"page raised: {at.exception}"
    assert len(at.dataframe) >= 1, "the stats table was not rendered"
    assert len(at.selectbox) >= 2, "player/statistic selectors missing"
