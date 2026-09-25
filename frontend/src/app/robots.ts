import type { MetadataRoute } from "next";

import { siteUrl } from "@/features/marketing/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/dashboard", "/orgs", "/settings", "/invite", "/login", "/register"],
    },
    sitemap: `${siteUrl()}/sitemap.xml`,
  };
}
