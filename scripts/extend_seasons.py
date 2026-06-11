"""Download the full demo bundle for additional seasons.

For every season passed on the command line it downloads, with the same
shape as the existing demo data: the six league-level datasets, the
complete per-team lineup population, every team's shot chart and a
play-by-play sample covering the 5 most recent games of each team.

Run from the repo root::

    python scripts/extend_seasons.py --seasons 2021-22 2022-23
    python scripts/extend_seasons.py --seasons 2021-22 --skip-pbp
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Repo root importable regardless of how the script is launched.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hoops_lab.ingestion.historical import (  # noqa: E402
    HistoricalDownloader,
    sample_game_ids_per_team,
)


def extend_season(downloader: HistoricalDownloader, season: str, skip_pbp: bool) -> int:
    """Download the complete bundle for one season; returns total rows."""
    results = downloader.download_season_bundle(season)
    results.append(downloader.download_lineups(season))
    results.extend(downloader.download_league_shot_charts(season))

    if not skip_pbp:
        team_box_path = next(r.path for r in results if r.dataset == "team_box")
        game_ids = sample_game_ids_per_team(pd.read_parquet(team_box_path), per_team=5)
        print(f"{season}: downloading play-by-play for {len(game_ids)} sampled games...")
        results.append(downloader.download_play_by_play(game_ids, season))

    rows = sum(r.rows for r in results)
    print(f"{season}: {len(results)} datasets, {rows:,} rows")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", nargs="+", required=True, help='e.g. "2021-22" "2022-23"')
    parser.add_argument("--skip-pbp", action="store_true", help="skip the play-by-play sample")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    downloader = HistoricalDownloader()
    total = sum(extend_season(downloader, season, args.skip_pbp) for season in args.seasons)
    print(f"Done — {total:,} rows across {len(args.seasons)} season(s) in {downloader.raw_dir}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
