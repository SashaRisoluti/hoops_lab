import type { MetadataRoute } from "next";

import { siteIndex } from "@/lib/data";
import { absoluteUrl } from "@/lib/site";

export const dynamic = "force-static";

// Routes are listed explicitly. When Phase 3 adds team and player pages they get
// generated from the index here, so the sitemap can never fall behind the pages.
const ROUTES = ["/", "/about"] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date(siteIndex.generatedAt);
  return ROUTES.map((route) => ({
    url: absoluteUrl(route),
    lastModified,
    changeFrequency: "monthly" as const,
    priority: route === "/" ? 1 : 0.7,
  }));
}
