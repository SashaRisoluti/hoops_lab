import { ImageResponse } from "next/og";

import { siteIndex } from "@/lib/data";
import { site } from "@/lib/site";
import tokens from "@/tokens.json";

// Generated at build time, so the shared link preview carries real numbers rather than
// a static screenshot that goes stale.
export const alt = `${site.name} — ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  const t = tokens.tokens;
  const { summary, latestSeason } = siteIndex;

  const facts = [
    [summary.seasons.toString(), "seasons"],
    [summary.games.toLocaleString("en-US"), "games"],
    [summary.shots.toLocaleString("en-US"), "shots parsed"],
  ];

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: t.bg_page,
          padding: 72,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 40 }}>🏀</div>
            <div style={{ fontSize: 34, fontWeight: 800, color: t.text }}>{site.name}</div>
          </div>
          <div
            style={{
              marginTop: 28,
              fontSize: 62,
              fontWeight: 800,
              color: t.text,
              lineHeight: 1.1,
              maxWidth: 940,
            }}
          >
            {site.tagline}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 56 }}>
            {facts.map(([value, label]) => (
              <div key={label} style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ fontSize: 44, fontWeight: 800, color: t.good }}>{value}</div>
                <div style={{ fontSize: 22, color: t.text_muted, marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 24, color: t.primary_soft }}>{`${latestSeason} season`}</div>
        </div>
      </div>
    ),
    size,
  );
}
