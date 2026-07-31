import type { ShotZone } from "@/lib/data";

/**
 * NBA half court with each zone shaded by its points per shot.
 *
 * Geometry is in real court units (tenths of a foot, the same system ShotChartDetail
 * uses): the hoop sits at the origin, the baseline at y = -47.5, the paint spans
 * x ∈ [-80, 80], the corner-three line sits at x = ±220 and the arc has radius 237.5.
 *
 * Zones are drawn largest-first and painted over by the smaller ones that sit inside
 * them, which avoids computing boolean geometry for shapes that are already nested.
 */

const ARC_R = 237.5;
const CORNER_X = 220;
const CORNER_Y = 92.5;
const PAINT_X = 80;
const PAINT_Y = 142.5;
const RA_R = 40;
const BASELINE = -47.5;
const TOP = 320;

/** Where the arc meets the vertical corner line, so the two never disagree. */
const ARC_Y = Math.sqrt(ARC_R * ARC_R - CORNER_X * CORNER_X);

type Band = "good" | "mid" | "weak";

/** Shade against the league average, so the colour means "better than the alternative". */
function band(pointsPerShot: number, average: number): Band {
  if (pointsPerShot >= average + 0.06) return "good";
  if (pointsPerShot <= average - 0.06) return "weak";
  return "mid";
}

// Large areas at full saturation read as an alert, not a diagram. These fills carry the
// same three-colour meaning as every other chart, just quietly enough to look at.
const FILL: Record<Band, string> = {
  good: "fill-good opacity-40",
  mid: "fill-mid opacity-30",
  weak: "fill-weak opacity-25",
};

function zoneFor(zones: ShotZone[], name: string): ShotZone | undefined {
  return zones.find((z) => z.zone === name);
}

function ZoneShape({
  zone,
  average,
  children,
}: {
  zone: ShotZone | undefined;
  average: number;
  children: (className: string) => React.ReactNode;
}) {
  if (!zone) return null;
  return <>{children(FILL[band(zone.pointsPerShot, average)])}</>;
}

export function CourtZones({
  zones,
  average,
  className,
}: {
  zones: ShotZone[];
  average: number;
  className?: string;
}) {
  const aboveBreak = zoneFor(zones, "Above the Break 3");
  const leftCorner = zoneFor(zones, "Left Corner 3");
  const rightCorner = zoneFor(zones, "Right Corner 3");
  const midRange = zoneFor(zones, "Mid-Range");
  const paint = zoneFor(zones, "In The Paint (Non-RA)");
  const restricted = zoneFor(zones, "Restricted Area");

  return (
    <svg
      viewBox={`-250 ${BASELINE} 500 ${TOP - BASELINE}`}
      className={className}
      role="img"
      aria-label="NBA half court shaded by points per shot in each zone"
    >
      {/* Court surface */}
      <rect x={-250} y={BASELINE} width={500} height={TOP - BASELINE} className="fill-card" />

      {/* Above the break: everything beyond the arc. Drawn first, painted over below. */}
      <ZoneShape zone={aboveBreak} average={average}>
        {(cls) => (
          <path
            className={cls}
            d={`M -250 ${ARC_Y} L -250 ${TOP} L 250 ${TOP} L 250 ${ARC_Y}
                L ${CORNER_X} ${ARC_Y} A ${ARC_R} ${ARC_R} 0 0 1 ${-CORNER_X} ${ARC_Y} Z`}
          />
        )}
      </ZoneShape>

      {/* Corner threes */}
      <ZoneShape zone={leftCorner} average={average}>
        {(cls) => (
          <rect className={cls} x={-250} y={BASELINE} width={30} height={CORNER_Y - BASELINE} />
        )}
      </ZoneShape>
      <ZoneShape zone={rightCorner} average={average}>
        {(cls) => (
          <rect className={cls} x={CORNER_X} y={BASELINE} width={30} height={CORNER_Y - BASELINE} />
        )}
      </ZoneShape>

      {/* Mid-range: inside the arc. Covers the middle of the above-break fill. */}
      <ZoneShape zone={midRange} average={average}>
        {(cls) => (
          <path
            className={cls}
            d={`M ${-CORNER_X} ${BASELINE} L ${-CORNER_X} ${ARC_Y}
                A ${ARC_R} ${ARC_R} 0 0 0 ${CORNER_X} ${ARC_Y}
                L ${CORNER_X} ${BASELINE} Z`}
          />
        )}
      </ZoneShape>

      {/* Paint, then the restricted area on top of it */}
      <ZoneShape zone={paint} average={average}>
        {(cls) => (
          <rect
            className={cls}
            x={-PAINT_X}
            y={BASELINE}
            width={PAINT_X * 2}
            height={PAINT_Y - BASELINE}
          />
        )}
      </ZoneShape>
      <ZoneShape zone={restricted} average={average}>
        {(cls) => <path className={cls} d={`M ${-RA_R} 0 A ${RA_R} ${RA_R} 0 0 0 ${RA_R} 0 Z`} />}
      </ZoneShape>

      {/* Court markings, drawn last so they read on top of the fills */}
      <g className="stroke-court" strokeWidth={2.5} fill="none">
        <rect x={-250} y={BASELINE} width={500} height={TOP - BASELINE} />
        <rect x={-PAINT_X} y={BASELINE} width={PAINT_X * 2} height={PAINT_Y - BASELINE} />
        <circle cx={0} cy={PAINT_Y} r={60} />
        <path d={`M ${-CORNER_X} ${BASELINE} L ${-CORNER_X} ${ARC_Y}`} />
        <path d={`M ${CORNER_X} ${BASELINE} L ${CORNER_X} ${ARC_Y}`} />
        <path
          d={`M ${-CORNER_X} ${ARC_Y} A ${ARC_R} ${ARC_R} 0 0 0 ${CORNER_X} ${ARC_Y}`}
        />
        <path d="M -30 -7.5 L 30 -7.5" strokeWidth={3} />
        <circle cx={0} cy={0} r={7.5} />
      </g>
    </svg>
  );
}
