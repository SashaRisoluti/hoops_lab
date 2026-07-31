/**
 * Label / value / sub-line KPI tile with an optional percentile bar.
 *
 * Mirrors `dashboard/components/stat_tile.py`, including its NaN handling: a missing
 * delta or percentile omits that block rather than rendering an empty one.
 */
const PCTL_GOOD = 66;
const PCTL_MID = 33;

function percentileClass(percentile: number): string {
  if (percentile >= PCTL_GOOD) return "bg-good";
  if (percentile >= PCTL_MID) return "bg-mid";
  return "bg-weak";
}

export function StatTile({
  label,
  value,
  sub,
  percentile,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  percentile?: number | null;
  accent?: string;
}) {
  const hasPercentile = typeof percentile === "number" && Number.isFinite(percentile);

  return (
    <div className="card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <p
        className="mt-1 font-display text-2xl font-bold tabular-nums"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </p>
      {sub ? <p className="mt-1 text-xs text-ink-soft">{sub}</p> : null}
      {hasPercentile ? (
        <div
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-line-soft"
          role="img"
          aria-label={`${Math.round(percentile)}th percentile`}
        >
          <div
            className={`h-full rounded-full ${percentileClass(percentile)}`}
            style={{ width: `${Math.min(100, Math.max(0, percentile))}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}
