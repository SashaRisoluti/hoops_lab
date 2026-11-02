import type { ComparisonRow } from "@/lib/live/types";

/**
 * Mirrored team comparison bars: away grows left, home grows right, the stat key sits in
 * the middle. Bar widths are percentages of their half; team colours come in as props.
 */
export function TeamComparison({
  rows,
  awayTricode,
  homeTricode,
  awayAccent,
  homeAccent,
}: {
  rows: ComparisonRow[];
  awayTricode: string;
  homeTricode: string;
  awayAccent: string;
  homeAccent: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-card p-4">
      <div className="mb-3 grid grid-cols-[1fr_4rem_1fr] items-center text-xs font-semibold uppercase tracking-wide text-ink-muted">
        <span>{awayTricode}</span>
        <span />
        <span className="text-right">{homeTricode}</span>
      </div>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.key} className="grid grid-cols-[1fr_4rem_1fr] items-center gap-x-2 text-sm">
            <div className="flex items-center justify-end gap-2">
              <span className="tabular-nums text-ink">{r.awayLabel}</span>
              <div className="flex h-2 w-full justify-end">
                <div
                  className="h-2 rounded-sm ring-1 ring-ink-faint"
                  style={{ width: `${r.awayWidth}%`, backgroundColor: awayAccent }}
                />
              </div>
            </div>
            <span className="text-center text-xs text-ink-muted">{r.key}</span>
            <div className="flex items-center gap-2">
              <div className="flex h-2 w-full">
                <div
                  className="h-2 rounded-sm ring-1 ring-ink-faint"
                  style={{ width: `${r.homeWidth}%`, backgroundColor: homeAccent }}
                />
              </div>
              <span className="tabular-nums text-ink">{r.homeLabel}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
