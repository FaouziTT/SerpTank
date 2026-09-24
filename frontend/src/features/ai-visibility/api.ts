/** Typed wrappers for AI visibility: settings, prompts, sampling, results, readiness. */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type AiSettings = S["AiSettingsOut"];
export type Prompt = S["PromptOut"];
export type PromptSuggestion = S["PromptSuggestion"];
export type Visibility = S["VisibilityOut"];
export type EngineVisibility = S["EngineVisibility"];
export type Rate = S["RateOut"];
export type Answer = S["AnswerOut"];
export type Readiness = S["ReadinessOut"];

const p = (org_id: string, project_id: string) => ({ params: { path: { org_id, project_id } } });
const promptPath = (org_id: string, project_id: string, prompt_id: string) => ({
  params: { path: { org_id, project_id, prompt_id } },
});

export const aiKeys = {
  all: (orgId: string, projectId: string) => ["orgs", orgId, "projects", projectId, "ai"],
};

export const aiApi = {
  settings: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/settings", p(orgId, projectId))),
  saveSettings: (orgId: string, projectId: string, brandTerms: string[], samples: number) =>
    unwrap(
      api.PUT("/api/v1/orgs/{org_id}/projects/{project_id}/ai/settings", {
        ...p(orgId, projectId),
        body: { brand_terms: brandTerms, samples_per_prompt: samples },
      }),
    ),
  prompts: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/prompts", p(orgId, projectId))),
  addPrompts: (
    orgId: string,
    projectId: string,
    marketId: string,
    prompts: string[],
    keyword: string | null = null,
  ) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/ai/prompts", {
        ...p(orgId, projectId),
        body: { market_id: marketId, prompts, keyword, engines: [] },
      }),
    ),
  setActive: (orgId: string, projectId: string, promptId: string, active: boolean) =>
    unwrap(
      api.PATCH("/api/v1/orgs/{org_id}/projects/{project_id}/ai/prompts/{prompt_id}", {
        ...promptPath(orgId, projectId, promptId),
        body: { active },
      }),
    ),
  removePrompt: (orgId: string, projectId: string, promptId: string) =>
    unwrap(
      api.DELETE(
        "/api/v1/orgs/{org_id}/projects/{project_id}/ai/prompts/{prompt_id}",
        promptPath(orgId, projectId, promptId),
      ),
    ),
  suggestions: (orgId: string, projectId: string, marketId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/prompts/suggestions", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { market_id: marketId } },
      }),
    ),
  run: (orgId: string, projectId: string) =>
    unwrap(api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/ai/run", p(orgId, projectId))),
  visibility: (orgId: string, projectId: string, days = 30) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/visibility", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { days } },
      }),
    ),
  answers: (orgId: string, projectId: string, engine?: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/answers", {
        params: {
          path: { org_id: orgId, project_id: projectId },
          query: engine ? { engine } : {},
        },
      }),
    ),
  readiness: (orgId: string, projectId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/ai/readiness", p(orgId, projectId)),
    ),
};
