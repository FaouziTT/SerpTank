/**
 * Public-site configuration, read on the server at request time.
 *
 * Operator details for the legal pages come from the environment so nothing is
 * invented: when they are missing the pages say so instead of showing placeholders.
 */
import "server-only";

import { serverApiGet } from "@/lib/api/server";
import type { components } from "@/lib/api/schema";

export type PublicPricing = components["schemas"]["PublicPricing"];
export type PublicConfig = components["schemas"]["PublicConfig"];

export function siteUrl(): string {
  return (process.env.SERPTANK_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");
}

export interface Operator {
  name: string | null;
  address: string | null;
  privacyEmail: string | null;
  securityEmail: string | null;
  jurisdiction: string | null;
}

export function operator(): Operator {
  const env = (key: string) => process.env[key]?.trim() || null;
  return {
    name: env("SERPTANK_LEGAL_ENTITY"),
    address: env("SERPTANK_LEGAL_ADDRESS"),
    privacyEmail: env("SERPTANK_PRIVACY_EMAIL"),
    securityEmail: env("SERPTANK_SECURITY_EMAIL"),
    jurisdiction: env("SERPTANK_LEGAL_JURISDICTION"),
  };
}

export async function publicPricing(): Promise<PublicPricing | null> {
  return (await serverApiGet<PublicPricing>("/api/v1/public/plans")).data;
}

export async function publicConfig(): Promise<PublicConfig | null> {
  return (await serverApiGet<PublicConfig>("/api/v1/public/config")).data;
}
