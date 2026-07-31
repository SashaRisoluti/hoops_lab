import type { Metadata } from "next";

import { PageHeader } from "@/components/PageHeader";
import { StatTile } from "@/components/StatTile";
import { siteIndex } from "@/lib/data";
import { absoluteUrl, site } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description: `How ${site.name} is built: the ingestion pipeline, the possession parser, the analytics engine and the stack behind it.`,
  alternates: { canonical: "/about" },
  openGraph: {
    title: `About — ${site.name}`,
    description: `How ${site.name} is built, from nba_api to DuckDB to the analytics package.`,
    url: absoluteUrl("/about"),
  },
};

const PIPELINE = [
  {
    step: "Ingestion",
    detail:
      "Every remote call goes through one throttled client — 0.6s minimum spacing, 30s timeout, retries. League datasets are one call per season; lineups and shot charts are fetched per team because the league endpoint caps at 2,000 rows.",
  },
  {
    step: "Storage",
    detail:
      "Parquet lands in DuckDB. SQL migrations own the structural tables, the seeder infers schemas straight from the files, and the database rebuilds itself from Parquet on boot — the demo host has an ephemeral filesystem.",
  },
  {
    step: "Possession parser",
    detail:
      "A state machine over play-by-play events segments the game into possessions. Points come from offence-team score deltas, which makes the output self-validating: a test reconstructs every final score in the database.",
  },
  {
    step: "Filter engine",
    detail:
      "Typed filter objects compile to parameterised SQL. Window operators become QUALIFY, which DuckDB evaluates after WHERE — that is what guarantees percentiles always describe the filtered population, never the full league.",
  },
  {
    step: "Models",
    detail:
      "Interpretable by design: logistic regression and shrinkage, trained on demand while excluding the game being viewed so nothing leaks. PER and BPM are deliberately not reimplemented — the endpoint values are used instead.",
  },
];

const STACK = [
  "Python 3.11",
  "nba_api",
  "DuckDB",
  "pandas",
  "scikit-learn",
  "Pydantic v2",
  "Streamlit",
  "Plotly",
  "Altair",
  "Next.js",
  "Tailwind",
  "pytest",
];

export default function AboutPage() {
  const { summary, project, seasons, generatedAt } = siteIndex;

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Person",
        name: site.author.name,
        url: site.url,
        sameAs: [site.author.github, site.author.linkedin].filter(Boolean),
      },
      {
        "@type": "Dataset",
        name: `${site.name} NBA dataset`,
        description: `Play-by-play, shot charts, lineups and box scores for ${summary.seasons} NBA seasons, aggregated into ${summary.possessions.toLocaleString("en-US")} parsed possessions.`,
        creator: { "@type": "Person", name: site.author.name },
        temporalCoverage: `${seasons[seasons.length - 1]}/${seasons[0]}`,
        isAccessibleForFree: true,
        url: absoluteUrl("/about"),
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        // Values come from the generated index, not user input.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <PageHeader
        title="How this is built"
        subtitle="A modular Python framework for NBA analysis. This site is its public face; the analytics live in an importable package, not in the UI."
        chips={["Python", "DuckDB", "Streamlit", "Next.js"]}
      />

      <section className="mb-12" aria-label="Project scale">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile
            label="Shots parsed"
            value={summary.shots.toLocaleString("en-US")}
            sub="with zone and coordinates"
          />
          <StatTile
            label="Possessions"
            value={summary.possessions.toLocaleString("en-US")}
            sub="segmented from play-by-play"
          />
          <StatTile label="Tests" value={String(project.tests)} sub="unit and integration" />
          <StatTile label="Python modules" value={String(project.modules)} sub="in hoops_lab/" />
        </div>
      </section>

      <section className="mb-12" aria-labelledby="pipeline">
        <h2 id="pipeline" className="text-2xl font-bold">
          The pipeline
        </h2>
        <p className="mt-2 max-w-2xl text-ink-soft">
          Data flows one way: <code className="text-primary-soft">nba_api → Parquet → DuckDB →
          analytics → interface</code>. Business logic lives only in the Python package; both the
          dashboard and this site are presentation layers over it.
        </p>

        <ol className="mt-6 space-y-4">
          {PIPELINE.map((entry, i) => (
            <li key={entry.step} className="card flex gap-4 p-5">
              <span
                aria-hidden
                className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-tile font-mono text-xs text-ink-muted"
              >
                {i + 1}
              </span>
              <div className="min-w-0">
                <h3 className="font-semibold">{entry.step}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{entry.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mb-12" aria-labelledby="quality">
        <h2 id="quality" className="text-2xl font-bold">
          How it is kept honest
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <div className="card p-5">
            <h3 className="font-semibold">Invariants, not assertions</h3>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">
              The possession parser is validated by reconstructing every final score in the
              database. If the segmentation is wrong, the arithmetic stops matching.
            </p>
          </div>
          <div className="card p-5">
            <h3 className="font-semibold">Quality gates on models</h3>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">
              Models must beat a baseline on a temporal holdout — log-loss for shot quality, AUC
              for win probability — or the build fails. Accuracy is a test, not a claim.
            </p>
          </div>
          <div className="card p-5">
            <h3 className="font-semibold">One source of truth for design</h3>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">
              This site&apos;s colours are generated from the dashboard&apos;s Python theme. A test
              fails if the two ever disagree, so the surfaces cannot drift apart.
            </p>
          </div>
        </div>
      </section>

      <section aria-labelledby="links">
        <h2 id="links" className="text-2xl font-bold">
          Stack and links
        </h2>
        <ul className="mt-4 flex flex-wrap gap-2">
          {STACK.map((tool) => (
            <li
              key={tool}
              className="rounded-full border border-line-soft bg-tile px-3 py-1 text-xs text-ink-muted"
            >
              {tool}
            </li>
          ))}
        </ul>

        <div className="mt-6 flex flex-wrap gap-3">
          <a
            href={site.author.github}
            className="rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Source on GitHub
          </a>
          {site.author.linkedin ? (
            <a
              href={site.author.linkedin}
              className="rounded-md border border-line-soft px-5 py-2.5 text-sm font-semibold text-ink-soft transition-colors hover:text-ink"
            >
              LinkedIn
            </a>
          ) : null}
          <a
            href={site.dashboardUrl}
            className="rounded-md border border-line-soft px-5 py-2.5 text-sm font-semibold text-ink-soft transition-colors hover:text-ink"
          >
            Live dashboard
          </a>
        </div>

        <p className="mt-8 text-xs text-ink-faint">
          Data generated {new Date(generatedAt).toISOString().slice(0, 10)} from the NBA Stats API
          via nba_api. Not affiliated with or endorsed by the NBA.
        </p>
      </section>
    </>
  );
}
