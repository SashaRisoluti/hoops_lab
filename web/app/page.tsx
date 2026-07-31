import { PageHeader } from "@/components/PageHeader";
import { StatTile } from "@/components/StatTile";
import { siteIndex } from "@/lib/data";
import { site } from "@/lib/site";

// The full hero — real leaders, team ratings and the archetype visual — lands in Task 5.
// This page exists now so the shell, tokens and data layer can be verified end to end.
export default function HomePage() {
  const { summary, latestSeason, generatedAt } = siteIndex;

  return (
    <>
      <PageHeader
        title={site.tagline}
        subtitle={site.description}
        chips={[`${summary.seasons} seasons`, `Latest: ${latestSeason}`]}
      />

      <section aria-label="Dataset at a glance">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile label="Seasons" value={String(summary.seasons)} sub="2021-22 to 2025-26" />
          <StatTile label="Teams" value={String(summary.teams)} />
          <StatTile label="Games" value={summary.games.toLocaleString("en-US")} />
          <StatTile label="Players" value={summary.players.toLocaleString("en-US")} />
        </div>
      </section>

      <p className="mt-8 text-xs text-ink-faint">
        Data generated {new Date(generatedAt).toISOString().slice(0, 10)}.
      </p>
    </>
  );
}
