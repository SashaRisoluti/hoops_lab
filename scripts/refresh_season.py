"""Weekly refresh of the in-progress season, end to end, in one command.

Downloads the season's full bundle (same shape as ``extend_seasons.py``),
publishes it to the versioned ``data/processed``, rebuilds DuckDB from exactly
what ships, re-exports the website data and, with ``--push``, commits and
pushes so Streamlit Cloud and Vercel redeploy. Run from the repo root, on a
network that can reach stats.nba.com, with the local dashboard stopped (it
holds the DuckDB file)::

    python scripts/refresh_season.py            # refresh, check the result locally
    python scripts/refresh_season.py --push     # refresh, commit and push
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# Repo root importable regardless of how the script is launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hoops_lab.config import DEMO_SEASONS  # noqa: E402
from hoops_lab.ingestion.historical import HistoricalDownloader  # noqa: E402
from hoops_lab.ingestion.nba_api_client import RAW_DATA_DIR  # noqa: E402
from hoops_lab.storage.database import Database  # noqa: E402
from hoops_lab.storage.seed import PROCESSED_DATA_DIR  # noqa: E402
from scripts.extend_seasons import extend_season  # noqa: E402

#: What a refresh changes in the repo, i.e. what ``--push`` commits.
PUBLISHED_PATHS = ("data/processed", "web/public/data")


def publish_season(season: str, raw_dir: Path, processed_dir: Path) -> list[Path]:
    """Copy one season's raw parquet files over the versioned ones."""
    copied = []
    for source in sorted(raw_dir.glob(f"*_{season}.parquet")):
        copied.append(Path(shutil.copy2(source, processed_dir / source.name)))
    return copied


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], check=False)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Refresh the in-progress season end to end.")
    parser.add_argument(
        "--season",
        default=max(DEMO_SEASONS),
        help="Season to refresh (default: the newest of DEMO_SEASONS).",
    )
    parser.add_argument("--skip-pbp", action="store_true", help="skip the play-by-play sample")
    parser.add_argument("--push", action="store_true", help="commit and push the refreshed data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    os.chdir(ROOT)  # every data path in the project is relative to the repo root

    extend_season(HistoricalDownloader(), args.season, args.skip_pbp)
    copied = publish_season(args.season, RAW_DATA_DIR, PROCESSED_DATA_DIR)
    print(f"{args.season}: published {len(copied)} files to {PROCESSED_DATA_DIR}")

    # Seed from data/processed so the local DB is exactly what the hosts rebuild.
    with Database() as db:
        db.ensure_db_ready(raw_dir=PROCESSED_DATA_DIR, force=True)
    subprocess.run([sys.executable, "scripts/export_web_data.py"], check=True)

    if not args.push:
        print("Done. Check the dashboard, then re-run with --push (or commit by hand).")
        return 0
    _git("add", *PUBLISHED_PATHS)
    if _git("diff", "--cached", "--quiet").returncode == 0:
        print("Nothing changed since the last refresh — nothing to push.")
        return 0
    message = f"data: refresh {args.season} ({date.today().isoformat()})"
    if _git("commit", "-m", message).returncode or _git("push").returncode:
        print("git commit/push failed — see the output above.")
        return 1
    print("Pushed: Streamlit Cloud and Vercel redeploy from main in a few minutes.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
