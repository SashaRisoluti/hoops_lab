/**
 * Single place for everything that depends on where the site lives and who wrote it.
 *
 * `url` is a placeholder until the real domain is confirmed. It is only used to build
 * absolute URLs for metadata, Open Graph and the sitemap, so changing it here updates
 * every page at once.
 */
export const site = {
  name: "Hoops Lab",
  tagline: "NBA analytics, from raw play-by-play to tactical insight",
  description:
    "A modular NBA data-science framework: historical analysis, pre-game scouting and live game intelligence, built on nba_api, DuckDB and Python.",
  // TODO: replace with the real custom domain before launch.
  url: "https://hoopslab.dev",
  author: {
    name: "Sasha Risoluti",
    github: "https://github.com/SashaRisoluti/hoops_lab",
    // TODO: confirm the LinkedIn URL and whether an email should be shown publicly.
    linkedin: null as string | null,
    email: null as string | null,
  },
  dashboardUrl: "https://huggingface.co/spaces/srisoluti/hoops-lab",
} as const;

/** Absolute URL for a site-relative path, for metadata and the sitemap. */
export function absoluteUrl(path: string): string {
  return new URL(path, site.url).toString();
}
