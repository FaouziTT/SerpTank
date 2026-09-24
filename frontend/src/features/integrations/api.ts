/** Typed wrappers for integrations, data sources, indexing and imports. */
import { api, ensureCsrfToken, unwrap } from "@/lib/api/client";
import { toApiError } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type Overview = S["IntegrationsOverview"];
export type ConnectionOut = S["ConnectionOut"];
export type Source = S["SourceOut"];
export type Performance = S["PerformanceOut"];
export type Vitals = S["VitalsOut"];
export type AiTotals = S["AiSurfaceTotals"];
export type Submission = S["SubmissionOut"];
export type Inspection = S["InspectionOut"];
export type ImportResult = S["ImportOut"];
export type GoogleFeature = "gsc" | "gsc_write" | "ga4" | "ads";
export type LinkableKind = "gsc" | "ga4" | "bing";

const org = (org_id: string) => ({ params: { path: { org_id } } });
const proj = (org_id: string, project_id: string) => ({ params: { path: { org_id, project_id } } });

export const integrationsApi = {
  overview: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/integrations", org(orgId))),
  startGoogle: (orgId: string, features: GoogleFeature[]) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/integrations/google/start", {
        ...org(orgId),
        body: { features },
      }),
    ),
  connectBing: (orgId: string, apiKey: string) =>
    unwrap(
      api.PUT("/api/v1/orgs/{org_id}/integrations/bing", {
        ...org(orgId),
        body: { api_key: apiKey },
      }),
    ),
  disconnect: (orgId: string, provider: "google" | "bing") =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/integrations/{provider}", {
        params: { path: { org_id: orgId, provider } },
      }),
    ),
  googleProperties: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/integrations/google/properties", org(orgId))),
  bingSites: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/integrations/bing/sites", org(orgId))),
};

export const sourcesApi = {
  list: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/sources", proj(orgId, projectId))),
  link: (orgId: string, projectId: string, kind: LinkableKind, propertyId: string) =>
    unwrap(
      api.PUT("/api/v1/orgs/{org_id}/projects/{project_id}/sources/{kind}", {
        params: { path: { org_id: orgId, project_id: projectId, kind } },
        body: { property_id: propertyId },
      }),
    ),
  unlink: (orgId: string, projectId: string, kind: LinkableKind) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/projects/{project_id}/sources/{kind}", {
        params: { path: { org_id: orgId, project_id: projectId, kind } },
      }),
    ),
  sync: (orgId: string, projectId: string, kind: LinkableKind | "vitals") =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/sources/{kind}/sync", {
        params: { path: { org_id: orgId, project_id: projectId, kind } },
      }),
    ),
  performance: (orgId: string, projectId: string, source: "gsc" | "bing", days: number) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/performance", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { source, days } },
      }),
    ),
  vitals: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/vitals", proj(orgId, projectId))),
  aiPerformance: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai-performance", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { days: 480 } },
      }),
    ),
};

export const indexingApi = {
  createKey: (orgId: string, projectId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/indexnow", proj(orgId, projectId)),
    ),
  verifyKey: (orgId: string, projectId: string) =>
    unwrap(
      api.POST(
        "/api/v1/orgs/{org_id}/projects/{project_id}/indexnow/verify",
        proj(orgId, projectId),
      ),
    ),
  setAuto: (orgId: string, projectId: string, auto_submit: boolean) =>
    unwrap(
      api.PATCH("/api/v1/orgs/{org_id}/projects/{project_id}/indexnow", {
        ...proj(orgId, projectId),
        body: { auto_submit },
      }),
    ),
  submit: (orgId: string, projectId: string, urls: string[], channel: "indexnow" | "bing") =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/submissions", {
        ...proj(orgId, projectId),
        body: { urls, channel },
      }),
    ),
  submissions: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/submissions", proj(orgId, projectId)),
    ),
  inspect: (orgId: string, projectId: string, url: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/inspections", {
        ...proj(orgId, projectId),
        body: { url },
      }),
    ),
  inspections: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/inspections", proj(orgId, projectId)),
    ),
};

/** Upload a CSV export as a raw text/csv body (streamed and size-checked by the API). */
export async function importCsv(
  orgId: string,
  projectId: string,
  source: "gsc_genai" | "bing_ai",
  file: Blob,
  surface?: string,
): Promise<ImportResult> {
  const query = surface ? `?surface=${encodeURIComponent(surface)}` : "";
  const res = await fetch(
    `${window.location.origin}/api/v1/orgs/${orgId}/projects/${projectId}/imports/${source}${query}`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "text/csv", "X-CSRF-Token": await ensureCsrfToken() },
      // Send bytes (not the Blob) so it works with every fetch implementation.
      body: await file.arrayBuffer(),
    },
  );
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, body);
  return body as ImportResult;
}

export const integrationKeys = {
  overview: (orgId: string) => ["integrations", orgId] as const,
  googleProps: (orgId: string) => ["integrations", orgId, "google-properties"] as const,
  bingSites: (orgId: string) => ["integrations", orgId, "bing-sites"] as const,
  project: (orgId: string, projectId: string) => ["search-data", orgId, projectId] as const,
};
