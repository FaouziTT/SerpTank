import type { MetadataRoute } from "next";

import { siteUrl } from "@/features/marketing/site";

const PAGES = ["", "/pricing", "/security", "/privacy", "/terms", "/dpa", "/subprocessors"];

export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.map((path) => ({ url: `${siteUrl()}${path || "/"}` }));
}
