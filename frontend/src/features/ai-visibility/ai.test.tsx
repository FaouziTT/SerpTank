import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { AiVisibilityPage, formatRate } from "./ai-page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
}));

const ORG = "0192f1a4-1b2c-7d3e-8f40-123456789abc";
const PROJECT = "0192f1a4-0000-7000-8000-000000000001";
const org = (role: Organization["role"] = "owner"): Organization => ({
  id: ORG,
  name: "A",
  slug: "a",
  plan_code: "pro",
  require_mfa: false,
  created_at: "2026-09-01T00:00:00Z",
  role,
});
const project: Project = {
  id: PROJECT,
  name: "Shop",
  primary_domain: "shop.com",
  verified: true,
  verification_method: "dns",
  crawl_schedule: "off",
  created_at: "2026-09-02T00:00:00Z",
  markets: [
    {
      id: "m1",
      country: "US",
      language: "en",
      location: null,
      device: "desktop",
      search_engines: ["google"],
      ai_engines: ["google_ai_overview", "chatgpt", "gemini"],
    },
  ],
};
const rate = (successes: number, trials: number, r: number | null, low: number, high: number) => ({
  successes,
  trials,
  rate: r,
  low,
  high,
});

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
  http.get("*/api/v1/orgs/:org/projects/:project/ai/visibility", () =>
    HttpResponse.json({
      days: 30,
      engines: [
        {
          engine: "chatgpt",
          samples: 3,
          answer_rate: rate(3, 3, 1, 0.44, 1),
          mention_rate: rate(2, 3, 0.6667, 0.2077, 0.9385),
          citation_rate: rate(1, 3, 0.3333, 0.0615, 0.7923),
          avg_sentiment: 0.5,
          avg_mention_rank: 1,
        },
      ],
      share_of_voice: [
        { domain: "shop.com", is_own: true, mentions: 2, citations: 1, share: 0.4 },
        { domain: "rival.com", is_own: false, mentions: 3, citations: 0, share: 0.6 },
      ],
      prompts: [],
      first_party: [],
    }),
  ),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

function renderPage(role: Organization["role"] = "owner") {
  renderWithQuery(
    <OrgProvider org={org(role)}>
      <AiVisibilityPage projectId={PROJECT} />
    </OrgProvider>,
  );
}

describe("AiVisibilityPage", () => {
  it("formats rates with their interval and sample size", () => {
    expect(formatRate(rate(2, 3, 0.6667, 0.2077, 0.9385))).toBe("67% (21–94%, n=3)");
    expect(formatRate(rate(0, 0, null, 0, 0))).toBe("—");
  });

  it("shows engine rates with intervals and share of voice", async () => {
    renderPage();
    expect(await screen.findByText("67% (21–94%, n=3)")).toBeInTheDocument();
    expect(screen.getByText("ChatGPT")).toBeInTheDocument();
    const row = screen.getByText("rival.com").closest("tr")!;
    expect(within(row).getByText("60%")).toBeInTheDocument();
    expect(screen.getByText(/Import the Search Console Gen-AI report/)).toBeInTheDocument();
  });

  it("marks unavailable engines and adds prompts", async () => {
    let body: unknown = null;
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/ai/settings", () =>
        HttpResponse.json({
          brand_terms: ["Shop"],
          samples_per_prompt: 3,
          prompts_used_this_month: 12,
          prompts_per_month: 2000,
          engines: [
            { engine: "chatgpt", selected: true, entitled: true, available: true, note: null },
            {
              engine: "gemini",
              selected: true,
              entitled: true,
              available: false,
              note: "No sampling adapter yet.",
            },
          ],
        }),
      ),
      http.get("*/api/v1/orgs/:org/projects/:project/ai/prompts", () => HttpResponse.json([])),
      http.get("*/api/v1/orgs/:org/projects/:project/ai/prompts/suggestions", () =>
        HttpResponse.json([
          {
            prompt: "What are the best trail shoes?",
            keyword: "trail shoes",
            intent: "commercial",
          },
        ]),
      ),
      http.post("*/api/v1/orgs/:org/projects/:project/ai/prompts", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ added: 1, skipped_existing: 0 }, { status: 201 });
      }),
    );
    renderPage();
    await userEvent.click(await screen.findByRole("tab", { name: "Prompts" }));
    expect(await screen.findByText("Gemini · not available")).toBeInTheDocument();
    expect(screen.getByText(/12 of 2,000 AI samples/)).toBeInTheDocument();
    expect(await screen.findByText("No prompts yet")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Add" }));
    await vi.waitFor(() =>
      expect(body).toEqual({
        market_id: "m1",
        prompts: ["What are the best trail shoes?"],
        keyword: "trail shoes",
        engines: [],
      }),
    );
  });

  it("explains readiness needs an audit", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/ai/readiness", () =>
        HttpResponse.json({
          available: false,
          score: null,
          crawl_id: null,
          components: [],
          bots: {},
          note: "Run a site audit to score AI readiness.",
        }),
      ),
    );
    renderPage("viewer");
    await userEvent.click(await screen.findByRole("tab", { name: "Readiness" }));
    expect(await screen.findByText("Run a site audit to score AI readiness.")).toBeInTheDocument();
  });
});
