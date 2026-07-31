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
  // The live deployment. Drives canonical links, Open Graph URLs and the sitemap, so it
  // must match the address the site is actually served from.
  url: "https://hoops-lab.vercel.app",
  author: {
    name: "Sasha Risoluti",
    github: "https://github.com/SashaRisoluti/hoops_lab",
    linkedin: "https://www.linkedin.com/in/sasha-risoluti/",
    email: null as string | null,
  },
  /** The live Streamlit dashboard. Community Cloud sleeps when idle, hence the warning. */
  dashboardUrl: "https://hoopslab.streamlit.app/",
} as const;

/** Absolute URL for a site-relative path, for metadata and the sitemap. */
export function absoluteUrl(path: string): string {
  return new URL(path, site.url).toString();
}
