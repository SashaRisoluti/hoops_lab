"""Export what the public web app needs from the Python side of the project.

The Streamlit dashboard and the web app must never disagree about colour. Rather than
maintaining a Tailwind config by hand, the design tokens are generated from
``dashboard/components/theme.py`` — the single source of truth — and committed. A unit
test re-runs the export and fails if the committed artifact has drifted.

Run from the repo root::

    python scripts/export_web_data.py --tokens-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root importable regardless of how the script is launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.theme import TEAM_ACCENTS_READABLE, TOKENS  # noqa: E402

#: Where the generated tokens live, relative to the repo root.
TOKENS_PATH = "web/tokens.json"

_SOURCE = "dashboard/components/theme.py"


def export_tokens(dest: Path) -> Path:
    """Write the design tokens and readable team accents to ``dest`` as JSON.

    The payload is deterministic on purpose: no timestamp, so re-running the export
    produces a byte-identical file and the drift gate stays meaningful.
    """
    payload = {
        "generatedFrom": _SOURCE,
        "tokens": dict(TOKENS),
        "teamAccents": dict(TEAM_ACCENTS_READABLE),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export web app data from the Python project.")
    parser.add_argument(
        "--tokens-only",
        action="store_true",
        help="Write only web/tokens.json (design tokens and team accents).",
    )
    args = parser.parse_args()

    written = export_tokens(ROOT / TOKENS_PATH)
    print(f"wrote {written.relative_to(ROOT)}")

    if not args.tokens_only:
        print("note: dataset export is not implemented yet — only tokens were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
