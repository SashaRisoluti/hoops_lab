"""Weekly refresh of the in-progress season, end to end, in one command.

Downloads the season's full bundle (same shape as ``extend_seasons.py``),
publishes it to the versioned ``data/processed``, rebuilds DuckDB from exactly
what ships, re-exports the website data and runs the full test suite as a
safety gate. With ``--push`` it then commits and pushes so Streamlit Cloud and
Vercel redeploy. Run from the repo root, on a network that can reach stats.nba.com,
with the local dashboard stopped (it holds the DuckDB file)::

    python scripts/refresh_season.py            # refresh, check the result locally
    python scripts/refresh_season.py --push     # refresh, commit and push

``--push`` is safe unattended (``scripts/schedule_refresh.ps1``): it runs only on
``main``, rebases on the latest remote main before downloading and again before
pushing (another PC may have pushed), never commits when the gate fails, and
commits only the published paths, so other work staged on the machine stays out.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import date, datetime
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


def _log(message: str) -> None:
    """Timestamped progress line (the scheduled run appends stdout to a log file)."""
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git, echoing its output so it lands in the same log, in order."""
    result = subprocess.run(
        ["git", *args], capture_output=True, encoding="utf-8", errors="replace", check=False
    )
    if output := (result.stdout + result.stderr).strip():
        print(output, flush=True)
    return result


def _pull() -> bool:
    """Rebase on the latest remote main; on failure leave the repo as it was."""
    if _git("pull", "--rebase", "--autostash").returncode == 0:
        return True
    _git("rebase", "--abort")  # never leave a half-done rebase for the next scheduled run
    _log("git pull --rebase failed (network, credentials or a conflict) - nothing pushed.")
    return False


def _gate_passes() -> bool:
    """Full test suite, Streamlit AppTests included, against the rebuilt DB."""
    gate = [sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider"]
    return subprocess.run(gate, check=False).returncode == 0


def refresh(season: str, skip_pbp: bool) -> None:
    """Download one season, publish it, rebuild DuckDB and re-export the web data."""
    extend_season(HistoricalDownloader(), season, skip_pbp)
    copied = publish_season(season, RAW_DATA_DIR, PROCESSED_DATA_DIR)
    _log(f"{season}: published {len(copied)} files to {PROCESSED_DATA_DIR}")

    # Seed from data/processed so the local DB is exactly what the hosts rebuild.
    with Database() as db:
        db.ensure_db_ready(raw_dir=PROCESSED_DATA_DIR, force=True)
    _log("DuckDB rebuilt from data/processed; exporting web data")
    subprocess.run([sys.executable, "scripts/export_web_data.py"], check=True)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="Refresh the in-progress season end to end.")
    parser.add_argument(
        "--season",
        default=max(DEMO_SEASONS),
        help="Season to refresh (default: the newest of DEMO_SEASONS).",
    )
    parser.add_argument("--skip-pbp", action="store_true", help="skip the play-by-play sample")
    parser.add_argument("--push", action="store_true", help="commit and push the refreshed data")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    os.chdir(ROOT)  # every data path in the project is relative to the repo root
    _log(f"refresh {args.season} started" + (" (--push)" if args.push else ""))

    if args.push:
        branch = _git("branch", "--show-current").stdout.strip()
        if branch != "main":
            _log(f"--push runs only on main, not on '{branch or 'detached HEAD'}' - aborted.")
            return 1
        if not _pull():
            return 1

    refresh(args.season, args.skip_pbp)
    _log("safety gate: running the full test suite")
    if not _gate_passes():
        _log("Safety gate FAILED - nothing committed or pushed, the live dashboard is untouched.")
        return 1

    if not args.push:
        _log("Done. Check the dashboard, then re-run with --push (or commit by hand).")
        return 0
    _git("add", "--", *PUBLISHED_PATHS)
    if _git("diff", "--cached", "--quiet", "--", *PUBLISHED_PATHS).returncode == 0:
        _log("Nothing changed since the last refresh - nothing to push.")
        return 0
    message = f"data: refresh {args.season} ({date.today().isoformat()})"
    # Pathspec: commit only the published paths, never other work staged on this machine.
    if _git("commit", "-m", message, "--", *PUBLISHED_PATHS).returncode:
        _log("git commit failed - see the output above.")
        return 1
    if not _pull() or _git("push").returncode:
        _log("git push failed - the data commit stays local; run `git push` by hand.")
        return 1
    _log("Pushed: Streamlit Cloud and Vercel redeploy from main in a few minutes.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    # The scheduled run's hidden console cannot report the exit code: the log does.
    try:
        code = main()
    except Exception:
        _log("FAILED with the exception below, exit code 1")
        raise
    _log(f"finished, exit code {code}")
    raise SystemExit(code)
