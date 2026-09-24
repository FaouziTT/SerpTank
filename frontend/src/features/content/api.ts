/** Typed wrappers for the on-page optimizer, content briefs, keyword map and cannibalization. */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type OptimizationSummary = S["OptimizationSummary"];
export type Optimization = S["OptimizationOut"];
export type BriefSummary = S["AnalysisSummary"];
export type Brief = S["BriefOut"];
export type KeywordMapRow = S["KeywordMapRow"];
export type CannibalizationReport = S["CannibalizationReport"];
export type AiUsage = S["AiUsageOut"];

/** Shape of `Optimization.result` (mirrors backend `onpage/analyzer.py` + service). */
export interface CheckResult {
  id: string;
  status: "pass" | "warn" | "fail" | "info";
  weight: number;
  message: string;
  recommendation: string;
  detail: { suggestions?: { url: string; title: string; relevance: string }[] } & Record<
    string,
    unknown
  >;
}
export interface CompetitorRow {
  position: number;
  domain: string;
  url: string;
  title: string;
  word_count: number | null;
  skipped: string | null;
  headings: string[];
}
export interface OptimizationResult {
  score: number;
  checks: CheckResult[];
  term_gaps: { term: string; competitors_using: number; median_uses: number; your_uses: number }[];
  benchmarks: { competitors_analyzed: number; word_count: number; median_word_count?: number };
  intent: { primary: string; reasons: string[] };
  competitors: CompetitorRow[];
  serp: {
    available: boolean;
    note: string | null;
    features: string[];
    own_position: number | null;
    ai_answer: boolean | null;
    ai_cited: boolean | null;
  };
}
export interface Rewrite {
  title: string;
  meta_description: string;
  h1: string;
  sections_to_add: string[];
  notes: string[];
}
/** Shape of `Brief.brief` (mirrors backend `onpage/brief.py`). */
export interface BriefData {
  keyword: string;
  intent: string;
  intent_reasons: string[];
  word_count_range: [number, number] | null;
  outline: { heading: string; pages: number; variants: string[] }[];
  questions: string[];
  terms: string[];
  secondary_keywords: string[];
  schema_type: string;
  serp_features: string[];
  ai_answer: { kind: string; cited_domains: string[] } | null;
  competitors: CompetitorRow[];
  internal_links: { url: string; title: string }[];
  notes: string[];
}

const p = (org_id: string, project_id: string) => ({ params: { path: { org_id, project_id } } });

export const contentKeys = {
  all: (orgId: string, projectId: string) => ["orgs", orgId, "projects", projectId, "content"],
};

export const contentApi = {
  optimizations: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/optimizer", p(orgId, projectId))),
  optimization: (orgId: string, projectId: string, id: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/optimizer/{optimization_id}", {
        params: { path: { org_id: orgId, project_id: projectId, optimization_id: id } },
      }),
    ),
  optimize: (orgId: string, projectId: string, marketId: string, keyword: string, url: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/optimizer", {
        ...p(orgId, projectId),
        body: { market_id: marketId, keyword, url },
      }),
    ),
  rewrite: (orgId: string, projectId: string, id: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/optimizer/{optimization_id}/rewrite", {
        params: { path: { org_id: orgId, project_id: projectId, optimization_id: id } },
      }),
    ),
  briefs: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/briefs", p(orgId, projectId))),
  brief: (orgId: string, projectId: string, id: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/briefs/{brief_id}", {
        params: { path: { org_id: orgId, project_id: projectId, brief_id: id } },
      }),
    ),
  createBrief: (orgId: string, projectId: string, marketId: string, keyword: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/briefs", {
        ...p(orgId, projectId),
        body: { market_id: marketId, keyword },
      }),
    ),
  markdownUrl: (orgId: string, projectId: string, id: string) =>
    `/api/v1/orgs/${orgId}/projects/${projectId}/briefs/${id}/markdown`,
  keywordMap: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/keyword-map", p(orgId, projectId))),
  setTarget: (orgId: string, projectId: string, keywordId: string, targetUrl: string | null) =>
    unwrap(
      api.PUT("/api/v1/orgs/{org_id}/projects/{project_id}/keyword-map/{keyword_id}", {
        params: { path: { org_id: orgId, project_id: projectId, keyword_id: keywordId } },
        body: { target_url: targetUrl },
      }),
    ),
  cannibalization: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/cannibalization", p(orgId, projectId)),
    ),
  aiUsage: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/ai-usage", { params: { path: { org_id: orgId } } })),
};
