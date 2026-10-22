import { CourtZones } from "@/components/CourtZones";
import { StatTile } from "@/components/StatTile";
import {
  accentFor,
  getLeaderboards,
  getShotZones,
  getTeamRatings,
  leagueAveragePps,
  siteIndex,
  zoneFgPct,
} from "@/lib/data";
import { site } from "@/lib/site";

function formatValue(key: string, value: number): string {
  return key === "TS_PCT" ? `${(value * 100).toFixed(1)}%` : value.toFixed(1);
}

export default async function HomePage() {
  const { summary, seasons, featuredSeason, generatedAt } = siteIndex;
  const [leaders, ratings, shotZones] = await Promise.all([
    getLeaderboards(featuredSeason),
    getTeamRatings(featuredSeason),
    getShotZones(featuredSeason),
  ]);

  const average = leagueAveragePps(shotZones.zones);
  const pct = (match: string) => `${(zoneFgPct(shotZones.zones, match) * 100).toFixed(1)}%`;
  const byEfficiency = [...shotZones.zones].sort((a, b) => b.pointsPerShot - a.pointsPerShot);
  const topTeams = [...ratings.teams]
    .filter((t) => t.netRating !== null)
    .sort((a, b) => (b.netRating ?? 0) - (a.netRating ?? 0))
    .slice(0, 5);

  return (
    <>
      {/* Hero */}
      <section className="mb-14">
        <p className="text-sm font-semibold uppercase tracking-widest text-primary-soft">
          {featuredSeason} season · live data
        </p>
        <h1 className="mt-3 max-w-3xl text-4xl font-extrabold leading-tight sm:text-5xl">
          {site.tagline}
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-ink-soft">{site.description}</p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <a
            href={site.dashboardUrl}
            className="rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Open the live dashboard
          </a>
          <a
            href={site.author.github}
            className="rounded-md border border-line-soft px-5 py-2.5 text-sm font-semibold text-ink-soft transition-colors hover:text-ink"
          >
            Read the source
          </a>
          <span className="text-xs text-ink-faint">
            The dashboard sleeps when idle and can take ~30s to wake.
          </span>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile label="Seasons" value={String(summary.seasons)} sub={`${seasons.at(-1)} to ${seasons[0]}`} />
          <StatTile label="Teams" value={String(summary.teams)} />
          <StatTile label="Games" value={summary.games.toLocaleString("en-US")} />
          <StatTile label="Players" value={summary.players.toLocaleString("en-US")} />
        </div>
      </section>

      {/* Signature visual */}
      <section className="mb-14" aria-labelledby="shot-value">
        <h2 id="shot-value" className="text-2xl font-bold">
          Where the points actually come from
        </h2>
        <p className="mt-2 max-w-2xl text-ink-soft">
          Field-goal percentage hides the answer. Priced in points per shot, a {pct("Corner 3")}{" "}
          corner three beats a {pct("Mid-Range")} mid-range jumper — which is why the mid-range has
          all but disappeared.
          Every zone below is {shotZones.totalAttempts.toLocaleString("en-US")} real attempts from
          the {featuredSeason} season.
        </p>

        <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="card p-4">
            <CourtZones zones={shotZones.zones} average={average} className="w-full" />
            <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm bg-good" />
                Above league average
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm bg-mid" />
                Around average
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm bg-weak" />
                Below average
              </span>
            </p>
          </div>

          <div className="card overflow-x-auto p-4">
            <table className="w-full text-sm">
              <caption className="sr-only">
                Points per shot and attempt share by court zone, {featuredSeason}
              </caption>
              <thead>
                <tr className="border-b border-line-soft text-left text-xs uppercase tracking-wide text-ink-muted">
                  <th scope="col" className="pb-2 font-medium">
                    Zone
                  </th>
                  <th scope="col" className="pb-2 text-right font-medium">
                    Share
                  </th>
                  <th scope="col" className="pb-2 text-right font-medium">
                    FG%
                  </th>
                  <th scope="col" className="pb-2 text-right font-medium">
                    Pts / shot
                  </th>
                </tr>
              </thead>
              <tbody>
                {byEfficiency.map((zone) => (
                  <tr key={zone.zone} className="border-b border-line-soft/50 last:border-0">
                    <th scope="row" className="py-2 pr-2 text-left font-normal">
                      {zone.zone}
                    </th>
                    <td className="py-2 text-right tabular-nums text-ink-soft">
                      {(zone.share * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-right tabular-nums text-ink-soft">
                      {(zone.fgPct * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-right font-semibold tabular-nums">
                      {zone.pointsPerShot.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-ink-faint">
              League average {average.toFixed(2)} points per shot. Zones under{" "}
              {shotZones.minAttempts} attempts are excluded.
            </p>
          </div>
        </div>
      </section>

      {/* Leaders */}
      <section className="mb-14" aria-labelledby="leaders">
        <h2 id="leaders" className="text-2xl font-bold">
          {featuredSeason} league leaders
        </h2>
        <p className="mt-2 text-ink-soft">
          Minimum {leaders.minGames} games and {leaders.minMinutes} minutes per game — a
          three-game cameo is not a scoring title.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {leaders.categories.map((category) => (
            <div key={category.key} className="card p-4">
              <h3 className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                {category.label}
              </h3>
              <ol className="mt-3 space-y-2">
                {category.leaders.slice(0, 5).map((leader, i) => (
                  <li key={leader.playerId} className="flex items-baseline gap-2 text-sm">
                    <span className="w-4 shrink-0 tabular-nums text-ink-faint">{i + 1}</span>
                    <span
                      aria-hidden
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: accentFor(leader.tricode) }}
                    />
                    <span className="min-w-0 flex-1 truncate">{leader.name}</span>
                    <span className="shrink-0 font-semibold tabular-nums">
                      {formatValue(category.key, leader.value)}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>

      {/* Team ratings */}
      <section aria-labelledby="teams">
        <h2 id="teams" className="text-2xl font-bold">
          Best net rating, {featuredSeason}
        </h2>
        <p className="mt-2 text-ink-soft">
          Point differential per 100 possessions, with the team&apos;s league percentile.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {topTeams.map((team) => (
            <StatTile
              key={team.id}
              label={team.name}
              value={`${(team.netRating ?? 0) > 0 ? "+" : ""}${(team.netRating ?? 0).toFixed(1)}`}
              sub={`${team.wins}-${team.losses} · ${team.offRating?.toFixed(1)} off / ${team.defRating?.toFixed(1)} def`}
              percentile={team.netRatingPctl}
              accent={accentFor(team.tricode)}
            />
          ))}
        </div>
      </section>

      <p className="mt-12 text-xs text-ink-faint">
        Data generated {new Date(generatedAt).toISOString().slice(0, 10)} from the NBA Stats API
        via nba_api. Descriptive analysis only — nothing here is a prediction.
      </p>
    </>
  );
}
