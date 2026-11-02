import type { ScoreboardGame } from "@/lib/live/types";
import { tipOffLabel } from "@/lib/live/format";

/**
 * Horizontally scrollable row of game chips: `AWY @ HOM`, the score (live/final) or the
 * tip-off time (scheduled), and a LIVE badge while in progress.
 */
export function GameChips({
  games,
  selectedId,
  onSelect,
  timeZone,
}: {
  games: ScoreboardGame[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  timeZone?: string;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {games.map((g) => {
        const selected = g.id === selectedId;
        const detail =
          g.state === "pre"
            ? tipOffLabel(g.startTime, timeZone)
            : `${g.away.score ?? 0}–${g.home.score ?? 0}`;
        return (
          <button
            key={g.id}
            type="button"
            aria-pressed={selected}
            onClick={() => onSelect(g.id)}
            className={`shrink-0 rounded-lg border px-3 py-2 text-left text-xs ${
              selected ? "border-ink bg-card" : "border-line bg-card text-ink-muted"
            }`}
          >
            <span className="block whitespace-nowrap font-medium">
              {g.away.tricode} @ {g.home.tricode}
            </span>
            <span className="mt-0.5 flex items-center gap-1.5 tabular-nums text-ink-soft">
              {detail}
              {g.state === "in" ? (
                <span className="rounded bg-weak px-1 text-[10px] font-bold uppercase text-card">
                  LIVE
                </span>
              ) : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}
