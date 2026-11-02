import type { TeamCounts } from "@/lib/live/types";

type Side = { tricode: string; score: number | null };

function TeamBlock({
  team,
  accent,
  fouls,
  timeouts,
  align,
}: {
  team: Side;
  accent: string;
  fouls: number | null;
  timeouts: number | null;
  align: "left" | "right";
}) {
  const right = align === "right";
  return (
    <div className={`min-w-0 flex-1 ${right ? "text-right" : "text-left"}`}>
      <p
        className={`flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-muted ${
          right ? "flex-row-reverse" : ""
        }`}
      >
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-ink-faint"
          style={{ backgroundColor: accent }}
        />
        {team.tricode}
      </p>
      <p className="font-display text-4xl font-bold tabular-nums">{team.score ?? "–"}</p>
      {fouls !== null && timeouts !== null ? (
        <p className="mt-1 text-xs text-ink-soft">
          Team fouls {fouls} · Timeouts used {timeouts}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Live scoreboard header: away block left, clock and status centre, home block right.
 * "Updated Ns ago" is computed from `updatedAt` at render time; the parent re-renders per poll.
 */
export function LiveScorebar({
  away,
  home,
  awayAccent,
  homeAccent,
  clock,
  fouls,
  timeouts,
  updatedAt,
  stale,
  tipOff,
  live,
}: {
  away: Side;
  home: Side;
  awayAccent: string;
  homeAccent: string;
  clock: string;
  fouls: TeamCounts | null;
  timeouts: TeamCounts | null;
  updatedAt: number | null;
  stale: boolean;
  tipOff: string | null;
  /** True only while the game is in progress (`state === "in"`); gates the LIVE marker. */
  live: boolean;
}) {
  const ago = updatedAt === null ? 0 : Math.max(0, Math.round((Date.now() - updatedAt) / 1000));
  const lastUpdate = updatedAt === null ? "–" : new Date(updatedAt).toLocaleTimeString();
  const counts = (side: "away" | "home") => ({
    fouls: fouls ? fouls[side] : null,
    timeouts: timeouts ? timeouts[side] : null,
  });

  return (
    <div className="card flex items-start gap-4 p-4">
      <TeamBlock team={away} accent={awayAccent} align="left" {...counts("away")} />
      <div className="min-w-0 max-w-[40%] shrink basis-1/3 text-center sm:max-w-xs">
        {tipOff !== null ? (
          <>
            <p className="font-display text-xl font-bold">Tip-off {tipOff}</p>
            <p className="mt-1 text-xs text-ink-soft">Reload the page once the game has started.</p>
          </>
        ) : (
          <>
            <p className="font-display text-xl font-bold tabular-nums">{clock}</p>
            {stale ? (
              <p className="mt-1 text-xs text-weak">
                Connection lost — retrying (last update {lastUpdate})
              </p>
            ) : (
              <p className="mt-1 text-xs text-ink-soft">
                {live ? `LIVE · updated ${ago}s ago · Data: ESPN` : "Data: ESPN"}
              </p>
            )}
          </>
        )}
      </div>
      <TeamBlock team={home} accent={homeAccent} align="right" {...counts("home")} />
    </div>
  );
}
