/** Typed wrappers for the technical-audit (crawl) and job APIs. */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type Crawl = S["CrawlOut"];
export type IssueSummary = S["IssueSummary"];
export type IssuePage = S["IssuePage"];
export type PageList = S["PageList"];
export type CrawlUsage = S["CrawlUsage"];
export type Job = S["JobOut"];
export type Severity = S["Severity"];
export type PageFilter =
  "all" | "html" | "indexable" | "non_indexable" | "redirects" | "errors" | "blocked";

const project = (org_id: string, project_id: string) => ({
  params: { path: { org_id, project_id } },
});
const crawl = (org_id: string, project_id: string, crawl_id: string) => ({
  params: { path: { org_id, project_id, crawl_id } },
});

export const auditApi = {
  usage: (orgId: string, projectId: string) =>
    unwrap(
      api.GET(
        "/api/v1/orgs/{org_id}/projects/{project_id}/crawls/usage",
        project(orgId, projectId),
      ),
    ),
  start: (orgId: string, projectId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/crawls", project(orgId, projectId)),
    ),
  list: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/crawls", project(orgId, projectId)),
    ),
  issues: (orgId: string, projectId: string, crawlId: string, engine: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/crawls/{crawl_id}/issues", {
        params: {
          path: { org_id: orgId, project_id: projectId, crawl_id: crawlId },
          query: { engine },
        },
      }),
    ),
  issueDetail: (
    orgId: string,
    projectId: string,
    crawlId: string,
    ruleId: string,
    offset: number,
  ) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/crawls/{crawl_id}/issues/{rule_id}", {
        params: {
          path: { org_id: orgId, project_id: projectId, crawl_id: crawlId, rule_id: ruleId },
          query: { limit: 50, offset },
        },
      }),
    ),
  pages: (
    orgId: string,
    projectId: string,
    crawlId: string,
    kind: PageFilter,
    q: string,
    offset: number,
  ) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/crawls/{crawl_id}/pages", {
        params: {
          ...crawl(orgId, projectId, crawlId).params,
          query: { kind, q: q || null, limit: 50, offset },
        },
      }),
    ),
};

export const jobsApi = {
  latest: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/jobs", {
        params: {
          path: { org_id: orgId },
          query: { project_id: projectId, kind: "crawl", limit: 1 },
        },
      }),
    ),
  get: (orgId: string, jobId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/jobs/{job_id}", {
        params: { path: { org_id: orgId, job_id: jobId } },
      }),
    ),
  cancel: (orgId: string, jobId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/jobs/{job_id}/cancel", {
        params: { path: { org_id: orgId, job_id: jobId } },
      }),
    ),
};

export const auditKeys = {
  all: (orgId: string, projectId: string) => ["audit", orgId, projectId] as const,
  usage: (orgId: string, projectId: string) => ["audit", orgId, projectId, "usage"] as const,
  crawls: (orgId: string, projectId: string) => ["audit", orgId, projectId, "crawls"] as const,
  activeJob: (orgId: string, projectId: string) => ["audit", orgId, projectId, "job"] as const,
  issues: (orgId: string, projectId: string, crawlId: string, engine: string) =>
    ["audit", orgId, projectId, crawlId, "issues", engine] as const,
  issue: (orgId: string, projectId: string, crawlId: string, ruleId: string) =>
    ["audit", orgId, projectId, crawlId, "issue", ruleId] as const,
  pages: (
    orgId: string,
    projectId: string,
    crawlId: string,
    kind: string,
    q: string,
    offset: number,
  ) => ["audit", orgId, projectId, crawlId, "pages", kind, q, offset] as const,
};

export const ACTIVE_JOB = new Set<Job["status"]>(["queued", "running"]);
