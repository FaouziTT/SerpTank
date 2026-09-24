/** Typed wrappers for keywords, rankings, competitors and research. */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type TrackedKeyword = S["TrackedKeywordOut"];
export type Position = S["PositionOut"];
export type Competitor = S["CompetitorOut"];
export type ShareOfVoice = S["ShareOfVoiceOut"];
export type Research = S["ResearchOut"];
export type Analysis = S["AnalyzeOut"];
export type Opportunities = S["OpportunitiesOut"];

const p = (org_id: string, project_id: string) => ({ params: { path: { org_id, project_id } } });

export const keywordsApi = {
  list: (orgId: string, projectId: string, marketId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/keywords", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { market_id: marketId } },
      }),
    ),
  add: (orgId: string, projectId: string, marketId: string, keywords: string[]) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/keywords", {
        ...p(orgId, projectId),
        body: { market_id: marketId, keywords, tags: [] },
      }),
    ),
  remove: (orgId: string, projectId: string, keywordId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/projects/{project_id}/keywords/{keyword_id}", {
        params: { path: { org_id: orgId, project_id: projectId, keyword_id: keywordId } },
      }),
    ),
  check: (orgId: string, projectId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/keywords/check", p(orgId, projectId)),
    ),
  competitors: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/competitors", p(orgId, projectId))),
  addCompetitor: (orgId: string, projectId: string, domain: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/competitors", {
        ...p(orgId, projectId),
        body: { domain, label: null },
      }),
    ),
  removeCompetitor: (orgId: string, projectId: string, competitorId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/projects/{project_id}/competitors/{competitor_id}", {
        params: { path: { org_id: orgId, project_id: projectId, competitor_id: competitorId } },
      }),
    ),
  shareOfVoice: (orgId: string, projectId: string, marketId: string, engine: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/keywords/share-of-voice", {
        params: {
          path: { org_id: orgId, project_id: projectId },
          query: { market_id: marketId, engine },
        },
      }),
    ),
  research: (orgId: string, projectId: string, marketId: string, seed: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/keywords/research", {
        ...p(orgId, projectId),
        body: { seed, market_id: marketId },
      }),
    ),
  analyze: (orgId: string, projectId: string, marketId: string, keyword: string, engine: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/keywords/analyze", {
        ...p(orgId, projectId),
        body: { keyword, market_id: marketId, engine },
      }),
    ),
  opportunities: (orgId: string, projectId: string) =>
    unwrap(
      api.GET(
        "/api/v1/orgs/{org_id}/projects/{project_id}/keywords/opportunities",
        p(orgId, projectId),
      ),
    ),
};

export const keywordKeys = {
  all: (orgId: string, projectId: string) => ["keywords", orgId, projectId] as const,
};
