import { periodLabel } from "@/lib/live/format";
import type { EspnWpPoint, GameState, WpPoint } from "@/lib/live/types";
import { displayPct } from "@/lib/live/winprob";

const QUARTER = 720;
const REGULATION = 2880;
const OVERTIME = 300;
// The plot stretches to its box (preserveAspectRatio="none"); strokes stay in screen
// pixels via vector-effect, and every label is HTML so text never scales with the box.
const W = 1000;
const H = 100;
const NO_SCALE = { vectorEffect: "non-scaling-stroke" } as const;

/** Elapsed game seconds → `Q3 4:58`; a buzzer play at t = 720 reads `Q1 0:00`. */
function clockAt(t: number): string {
  const ot = t > REGULATION ? Math.ceil((t - REGULATION) / OVERTIME) : 0;
  const period = ot ? 4 + ot : Math.max(1, Math.ceil(t / QUARTER));
  const s = Math.floor((ot ? REGULATION + ot * OVERTIME : period * QUARTER) - t);
  return `${periodLabel(period)} ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function TeamPct({
  tricode,
  accent,
  value,
  align,
}: {
  tricode: string;
  accent: string;
  value: number;
  align: "left" | "right";
}) {
  const right = align === "right";
  return (
    <div className={right ? "text-right" : "text-left"}>
      <p
        className={`flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-muted ${
          right ? "flex-row-reverse" : ""
        }`}
      >
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-ink-soft"
          style={{ backgroundColor: accent }}
        />
        {tricode}
      </p>
      <p className="font-display text-3xl font-bold">{value}%</p>
    </div>
  );
}

/**
 * Win probability for the selected game, layout A: away/home percentages and a split bar,
 * then (once the game has started) home win probability over elapsed game time — our model
 * solid, ESPN dashed — over the score margin as a muted stepped area on a right axis whose
 * 0 sits on the 50% line, so "home leads" and "home favoured" share a side.
 */
export function WinProbabilityCard({
  homeTricode,
  awayTricode,
  homeAccent,
  awayAccent,
  state,
  current,
  pregame,
  series,
  espn,
  periods,
  asOf,
  metrics,
  note,
}: {
  /** Optional small muted line under the footnote. */
  note?: string;
  homeTricode: string;
  awayTricode: string;
  homeAccent: string;
  awayAccent: string;
  state: GameState;
  /** Home win probability now (last point of `series`); `null` falls back to `pregame`. */
  current: number | null;
  pregame: number;
  series: WpPoint[];
  espn: EspnWpPoint[];
  /** Periods to lay out on the x axis, at least 4; each one beyond 4 adds a 5-minute OT. */
  periods: number;
  asOf: string;
  metrics: { fitGames: number; holdoutGames: number; holdoutLogLoss: number; baselineLogLoss: number };
}) {
  const started = state !== "pre";
  const live = state === "in";
  // Headline numbers are clamped to 1–99 while live; the curve itself stays exact.
  const homePct = displayPct(started ? (current ?? pregame) : pregame, live);
  const lastEspn = started ? espn[espn.length - 1] : undefined;
  const espnPct = lastEspn ? displayPct(lastEspn.home, live) : 0;
  const pre = displayPct(pregame, false);
  const lead = (m: number) =>
    m === 0 ? "tied" : `${m > 0 ? homeTricode : awayTricode} +${Math.abs(m)}`;

  return (
    <section className="card p-4">
      <div className="flex items-end justify-between gap-4">
        <TeamPct tricode={awayTricode} accent={awayAccent} value={100 - homePct} align="left" />
        <div className="pb-1 text-center">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
            Win probability
          </h2>
          {lastEspn ? (
            <p className="mt-0.5 text-xs text-ink-soft">
              ESPN: {espnPct >= 50 ? `${homeTricode} ${espnPct}` : `${awayTricode} ${100 - espnPct}`}%
            </p>
          ) : null}
        </div>
        <TeamPct tricode={homeTricode} accent={homeAccent} value={homePct} align="right" />
      </div>
      <div aria-hidden className="mt-3 flex h-2 gap-0.5">
        {homePct < 100 ? (
          <div
            className="rounded-sm ring-1 ring-ink-soft"
            style={{ flex: 100 - homePct, backgroundColor: awayAccent }}
          />
        ) : null}
        {homePct > 0 ? (
          <div
            className="rounded-sm ring-1 ring-ink-soft"
            style={{ flex: homePct, backgroundColor: homeAccent }}
          />
        ) : null}
      </div>

      {started && series.length ? (
        <Chart
          homeTricode={homeTricode}
          awayTricode={awayTricode}
          live={live}
          homePct={homePct}
          espnPct={lastEspn ? espnPct : null}
          series={series}
          espn={espn}
          periods={periods}
          lead={lead}
        />
      ) : null}

      <p className="mt-3 text-xs text-ink-soft">
        Pregame: {pre >= 50 ? `${homeTricode} ${pre}` : `${awayTricode} ${100 - pre}`}% (season net
        rating + home court, as of {asOf}) · fitted on {metrics.fitGames} games · held-out
        log-loss {metrics.holdoutLogLoss.toFixed(3)} on {metrics.holdoutGames} games (score-and-clock
        baseline {metrics.baselineLogLoss.toFixed(3)})
      </p>
      {note ? <p className="mt-1 text-xs text-ink-muted">{note}</p> : null}
    </section>
  );
}

function Chart({
  homeTricode,
  awayTricode,
  live,
  homePct,
  espnPct,
  series,
  espn,
  periods,
  lead,
}: {
  homeTricode: string;
  awayTricode: string;
  live: boolean;
  homePct: number;
  espnPct: number | null;
  series: WpPoint[];
  espn: EspnWpPoint[];
  periods: number;
  lead: (margin: number) => string;
}) {
  const spans = Array.from({ length: Math.max(4, periods) }, (_, i) => {
    const start = i < 4 ? i * QUARTER : REGULATION + (i - 4) * OVERTIME;
    return { label: periodLabel(i + 1), start, end: start + (i < 4 ? QUARTER : OVERTIME) };
  });
  const total = spans[spans.length - 1].end;
  const x = (t: number) => (Math.min(t, total) / total) * W;
  const yP = (p: number) => (1 - p) * H;
  const maxMargin = Math.max(0, ...series.map((s) => Math.abs(s.margin)));
  const M = Math.max(10, Math.ceil(maxMargin / 5) * 5);
  const yM = (m: number) => H / 2 - (m / M) * (H / 2);
  const line = (ps: { t: number; home: number }[]) =>
    ps.map((p) => `${x(p.t)},${yP(p.home)}`).join(" ");

  // Scores change in steps: hold the previous margin until the next scoring play.
  const steps = series
    .map((s, i) => `${i ? `H${x(s.t)}` : `M${x(s.t)} ${H / 2}`} V${yM(s.margin)}`)
    .join(" ");
  const last = series[series.length - 1];

  // ESPN's value at each of our points (its latest play at or before t), for the tooltips.
  let j = -1;
  const espnAt = series.map((s) => {
    while (j + 1 < espn.length && espn[j + 1].t <= s.t) j++;
    return j >= 0 ? espn[j].home : null;
  });

  const aria =
    `Win probability over the game: ${homeTricode} ${homePct}%, ${awayTricode} ${100 - homePct}%` +
    (espnPct === null ? "" : `; ESPN ${homeTricode} ${espnPct}%`) +
    `; score margin ${lead(last.margin)}.`;

  return (
    <>
      <div className="mt-4 grid grid-cols-[auto_1fr_auto] gap-x-2 text-[11px] leading-3 text-ink-soft tabular-nums">
        {/* Labels sit centred on the plot's top edge, midline and bottom edge. */}
        <div aria-hidden className="-my-1.5 flex flex-col justify-between text-right">
          <span>{homeTricode} 100%</span>
          <span>50%</span>
          <span>{awayTricode} 100%</span>
        </div>
        <div className="relative h-44 sm:h-52">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            className="absolute inset-0 h-full w-full overflow-visible"
            role="img"
            aria-label={aria}
          >
            <g className="stroke-grid" strokeWidth={1}>
              <line x1={0} x2={W} y1={0} y2={0} {...NO_SCALE} />
              <line x1={0} x2={W} y1={H} y2={H} {...NO_SCALE} />
              {spans.slice(1).map((s) => (
                <line key={s.start} x1={x(s.start)} x2={x(s.start)} y1={0} y2={H} {...NO_SCALE} />
              ))}
            </g>
            <path d={`${steps} V${H / 2} Z`} className="fill-ink-muted" fillOpacity={0.2} />
            <path
              d={steps}
              fill="none"
              className="stroke-ink-muted"
              strokeWidth={1}
              strokeOpacity={0.8}
              {...NO_SCALE}
            />
            <line
              x1={0}
              x2={W}
              y1={H / 2}
              y2={H / 2}
              className="stroke-ink-faint"
              strokeWidth={1}
              strokeDasharray="3 3"
              {...NO_SCALE}
            />
            {espn.length ? (
              <polyline
                points={line(espn)}
                fill="none"
                className="stroke-ink-soft"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                strokeLinejoin="round"
                {...NO_SCALE}
              />
            ) : null}
            <polyline
              points={line(series)}
              fill="none"
              className="stroke-primary-soft"
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              {...NO_SCALE}
            />
            {/* Hover targets: one full-height strip per point, native tooltip, no state. */}
            {series.map((s, i) => {
              const from = i ? (x(series[i - 1].t) + x(s.t)) / 2 : 0;
              const to = i < series.length - 1 ? (x(s.t) + x(series[i + 1].t)) / 2 : W;
              const e = espnAt[i];
              return (
                <rect key={i} x={from} width={Math.max(0, to - from)} y={0} height={H} fill="transparent">
                  <title>
                    {`${clockAt(s.t)} · ${homeTricode} ${displayPct(s.home, live)}%` +
                      (e === null ? "" : ` (ESPN ${displayPct(e, live)}%)`) +
                      ` · ${lead(s.margin)}`}
                  </title>
                </rect>
              );
            })}
          </svg>
          {live ? (
            <span
              aria-hidden
              className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary-soft ring-2 ring-card"
              style={{ left: `${(x(last.t) / W) * 100}%`, top: `${(yP(last.home) / H) * 100}%` }}
            />
          ) : null}
        </div>
        <div aria-hidden className="-my-1.5 flex flex-col justify-between">
          <span>+{M}</span>
          <span>0</span>
          <span>−{M}</span>
        </div>
        <span />
        <div aria-hidden className="relative mt-1.5 h-3">
          {spans.map((s) => (
            <span
              key={s.start}
              className="absolute -translate-x-1/2"
              style={{ left: `${(x((s.start + s.end) / 2) / W) * 100}%` }}
            >
              {s.label}
            </span>
          ))}
        </div>
        <span aria-hidden className="mt-1.5">
          pts
        </span>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-0.5 w-4 rounded-full bg-primary-soft" />
          Hoops Lab model
        </li>
        {espn.length ? (
          <li className="flex items-center gap-1.5">
            <span aria-hidden className="w-4 border-t-2 border-dashed border-ink-soft" />
            ESPN
          </li>
        ) : null}
        <li className="flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-4 border-t border-ink-muted bg-ink-muted/20" />
          Score margin (right axis, home − away)
        </li>
      </ul>
    </>
  );
}
