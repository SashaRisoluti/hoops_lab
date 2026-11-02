import type { CourtShot, Side } from "@/lib/live/types";

/**
 * Full NBA court (94 x 50 ft) with the most recent shots and a possession pill.
 *
 * Geometry is in real feet. The away team attacks the left basket (x 5.25) and the home
 * team the right (x 88.75); `CourtShot` coordinates are already in this frame. Team
 * colours arrive as props and go in inline styles, with a light outline so black stays
 * visible on the court.
 */

const LEN = 94;
const WID = 50;
const MID = WID / 2;
const HOOP_X = 5.25;
const ARC_R = 23.75;
const CORNER_Y = 3;
const PAINT_DEPTH = 19;
const PAINT_HALF = 8;
const CIRCLE_R = 6;

/** Distance along x from the hoop to where the arc meets a corner line. */
const ARC_DX = Math.sqrt(ARC_R * ARC_R - (MID - CORNER_Y) ** 2);

/** Markings for one basket: left baseline by default, mirrored to the right with `flip`. */
function Basket({ flip }: { flip: boolean }) {
  const x = (v: number) => (flip ? LEN - v : v);
  const sweep = flip ? 0 : 1;
  const arcX = x(HOOP_X + ARC_DX);
  return (
    <>
      <rect
        x={flip ? LEN - PAINT_DEPTH : 0}
        y={MID - PAINT_HALF}
        width={PAINT_DEPTH}
        height={PAINT_HALF * 2}
      />
      <path
        d={`M ${x(PAINT_DEPTH)} ${MID - CIRCLE_R} A ${CIRCLE_R} ${CIRCLE_R} 0 0 ${sweep} ${x(PAINT_DEPTH)} ${MID + CIRCLE_R}`}
      />
      <path
        d={`M ${x(0)} ${CORNER_Y} L ${arcX} ${CORNER_Y} A ${ARC_R} ${ARC_R} 0 0 ${sweep} ${arcX} ${WID - CORNER_Y} L ${x(0)} ${WID - CORNER_Y}`}
      />
      <path d={`M ${x(4)} ${MID - 3} L ${x(4)} ${MID + 3}`} />
      <circle cx={x(HOOP_X)} cy={MID} r={0.75} />
    </>
  );
}

export function LiveCourt({
  shots,
  possession,
  awayTricode,
  homeTricode,
  awayAccent,
  homeAccent,
  lastPlay,
}: {
  shots: CourtShot[];
  possession: Side | null;
  awayTricode: string;
  homeTricode: string;
  awayAccent: string;
  homeAccent: string;
  lastPlay: string | null;
}) {
  const accent = (side: Side) => (side === "home" ? homeAccent : awayAccent);
  const owner = possession === "home" ? homeTricode : awayTricode;
  const aria = `Basketball court, ${
    possession ? `${owner} has possession` : "no team in possession"
  }, ${shots.length} recent shots`;

  return (
    <div>
      <div className="relative">
        <svg viewBox={`0 0 ${LEN} ${WID}`} className="w-full" role="img" aria-label={aria}>
          <rect width={LEN} height={WID} className="fill-card" />
          <g className="stroke-court" strokeWidth={0.3} fill="none">
            <rect width={LEN} height={WID} />
            <path d={`M ${LEN / 2} 0 L ${LEN / 2} ${WID}`} />
            <circle cx={LEN / 2} cy={MID} r={CIRCLE_R} />
            <Basket flip={false} />
            <Basket flip />
          </g>
          {shots.map((s, i) => (
            <g key={i}>
              <title>{`${s.made ? "Made" : "Missed"}: ${s.text}`}</title>
              {/* Light halo under the team colour so a black accent stays visible. */}
              <circle cx={s.courtX} cy={s.courtY} r={0.9} strokeWidth={0.8} fill="none" className="stroke-ink-soft" />
              <circle
                cx={s.courtX}
                cy={s.courtY}
                r={0.9}
                strokeWidth={0.4}
                style={s.made ? { fill: accent(s.side), stroke: accent(s.side) } : { fill: "none", stroke: accent(s.side) }}
              />
            </g>
          ))}
        </svg>
        {/* Neutral pill with a team swatch: white text on a light accent would be unreadable. */}
        {possession && (
          <span className="absolute left-1/2 top-2 flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full bg-page px-3 py-1 text-xs font-semibold text-ink ring-1 ring-ink-soft">
            {possession === "away" && "◄"}
            <span
              aria-hidden
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-ink-soft"
              style={{ backgroundColor: accent(possession) }}
            />
            {possession === "home" ? `${homeTricode} ATTACKING ►` : `${awayTricode} ATTACKING`}
          </span>
        )}
      </div>
      {lastPlay && <p className="mt-2 text-sm text-ink-muted">Last play: {lastPlay}</p>}
    </div>
  );
}
