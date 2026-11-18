"""Download the full demo bundle for additional seasons.

For every season passed on the command line it downloads, with the same
shape as the existing demo data: the six league-level datasets, the
complete per-team lineup population, every team's shot chart and a
play-by-play sample covering the 5 most recent games of each team.

With ``--pbp-random N`` it downloads nothing else: it adds N games drawn uniformly from the
whole regular season (seeded) to the published play-by-play sample in data/processed, for
complete seasons only. The download checkpoints every game under data/raw/pbp_games and
logs to data/raw/pbp_sample.log, so re-running the same command resumes an interrupted run.
The merged sample is staged in data/raw; publish it to data/processed by hand.

Run from the repo root::

    python scripts/extend_seasons.py --seasons 2021-22 2022-23
    python scripts/extend_seasons.py --seasons 2021-22 --skip-pbp
    python scripts/extend_seasons.py --seasons 2021-22 2022-23 --pbp-random 250
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
    random_season_game_ids,
    sample_game_ids_per_team,
)
from hoops_lab.ingestion.schemas import DownloadResult  # noqa: E402
from hoops_lab.models.game_win_probability import SEASON_GAMES  # noqa: E402
from hoops_lab.storage.seed import PROCESSED_DATA_DIR  # noqa: E402

#: Seed of the whole-season PBP sample: the same command always picks the same games.
PBP_SEED = 0


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


def extend_pbp_sample(
    downloader: HistoricalDownloader,
    season: str,
    n: int,
    seed: int = PBP_SEED,
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> DownloadResult:
    """Union ``n`` whole-season random games with the published PBP sample of ``season``.

    Reads the published team_box and play-by-play sample from ``processed_dir`` and stages
    the merged sample in the downloader's raw_dir. Exits for an incomplete season: the
    in-progress season belongs to scripts/refresh_season.py.
    """
    team_box = pd.read_parquet(Path(processed_dir) / f"team_box_{season}.parquet")
    games = team_box["GAME_ID"].astype(str)
    if games[games.str.startswith("002")].nunique() < SEASON_GAMES:
        raise SystemExit(f"{season} is not complete ({games.nunique()} games): refusing")
    published = Path(processed_dir) / f"play_by_play_sample_{season}.parquet"
    existing = pd.read_parquet(published) if published.exists() else None
    game_ids = random_season_game_ids(team_box, n, seed)
    return downloader.download_play_by_play_resumable(game_ids, season, existing)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", nargs="+", required=True, help='e.g. "2021-22" "2022-23"')
    parser.add_argument("--skip-pbp", action="store_true", help="skip the play-by-play sample")
    parser.add_argument(
        "--pbp-random",
        type=int,
        metavar="N",
        help="only add N random whole-season games to the published PBP sample (resumable)",
    )
    args = parser.parse_args()

    downloader = HistoricalDownloader()
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.pbp_random:
        downloader.raw_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(downloader.raw_dir / "pbp_sample.log"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    if args.pbp_random:
        for season in args.seasons:
            result = extend_pbp_sample(downloader, season, args.pbp_random)
            logging.info(
                "%s: %d events in %d games -> %s",
                season,
                result.rows,
                pd.read_parquet(result.path)["gameId"].nunique(),
                result.path,
            )
        return
    total = sum(extend_season(downloader, season, args.skip_pbp) for season in args.seasons)
    print(f"Done — {total:,} rows across {len(args.seasons)} season(s) in {downloader.raw_dir}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
