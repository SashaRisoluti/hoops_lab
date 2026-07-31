import type { Metadata } from "next";

import { PageHeader } from "@/components/PageHeader";
import { siteIndex } from "@/lib/data";
import { absoluteUrl, site } from "@/lib/site";

// The engineering story, architecture diagram and JSON-LD land in Task 6.
export const metadata: Metadata = {
  title: "About",
  description: `How ${site.name} is built: the data pipeline, the analytics engine and the stack behind it.`,
  alternates: { canonical: "/about" },
  openGraph: {
    title: `About — ${site.name}`,
    description: `How ${site.name} is built.`,
    url: absoluteUrl("/about"),
  },
};

export default function AboutPage() {
  return (
    <>
      <PageHeader
        title="About this project"
        subtitle={site.description}
        chips={["Python", "DuckDB", "Streamlit", "Next.js"]}
      />

      <section className="card max-w-2xl p-6">
        <h2 className="text-lg font-bold">Data pipeline</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          NBA Stats API via nba_api → Parquet → DuckDB → the <code>hoops_lab</code> analytics
          package. This site renders {siteIndex.summary.games.toLocaleString("en-US")} games across{" "}
          {siteIndex.summary.seasons} seasons, exported to static JSON at build time so nothing is
          computed in the browser.
        </p>
        <a
          href={site.author.github}
          className="mt-4 inline-block text-sm font-semibold text-primary-soft hover:underline"
        >
          Source on GitHub →
        </a>
      </section>
    </>
  );
}
