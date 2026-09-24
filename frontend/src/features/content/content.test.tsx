import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { ContentPage } from "./content-page";

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
      ai_engines: [],
    },
  ],
};
const summary = {
  id: "o1",
  market_id: "m1",
  keyword: "trail shoes",
  status: "completed",
  error: null,
  created_at: "2026-09-24T00:00:00Z",
  url: "https://shop.com/trail",
  score: 42,
};
const detail = {
  ...summary,
  rewrite: null,
  result: {
    score: 42,
    checks: [
      {
        id: "title_keyword",
        status: "fail",
        weight: 12,
        message: "The page has no <title>.",
        recommendation: "Add a unique, descriptive title.",
        detail: {},
      },
      {
        id: "internal_links",
        status: "warn",
        weight: 6,
        message: "1 internal page(s) link here.",
        recommendation: "Link to this page from related pages.",
        detail: {
          suggestions: [{ url: "https://shop.com/guide", title: "Trail guide", relevance: "100%" }],
        },
      },
    ],
    term_gaps: [{ term: "cushioning", competitors_using: 3, median_uses: 4, your_uses: 0 }],
    benchmarks: { competitors_analyzed: 3, word_count: 40 },
    intent: { primary: "commercial", reasons: [] },
    competitors: [
      {
        position: 1,
        domain: "gear.example",
        url: "https://gear.example/x",
        title: "t",
        word_count: 900,
        skipped: null,
        headings: [],
      },
      {
        position: 2,
        domain: "blocked.example",
        url: "https://blocked.example/x",
        title: "t",
        word_count: null,
        skipped: "robots",
        headings: [],
      },
    ],
    serp: {
      available: true,
      note: null,
      features: [],
      own_position: 3,
      ai_answer: true,
      ai_cited: false,
    },
  },
};

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
  http.get("*/api/v1/orgs/:org/projects/:project/optimizer", () => HttpResponse.json([summary])),
  http.get("*/api/v1/orgs/:org/projects/:project/optimizer/:id", () => HttpResponse.json(detail)),
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
      <ContentPage projectId={PROJECT} />
    </OrgProvider>,
  );
}

describe("ContentPage", () => {
  it("explains the analysis and shows AI failures honestly", async () => {
    server.use(
      http.post("*/api/v1/orgs/:org/projects/:project/optimizer/:id/rewrite", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "AI suggestions are unavailable",
            status: 503,
            code: "llm_unavailable",
            detail: "AI suggestions aren't configured on this server.",
          },
          { status: 503, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    renderPage();
    expect(await screen.findByLabelText("Score 42 out of 100")).toBeInTheDocument();
    const checks = screen.getByRole("list", { name: "Checks" });
    expect(within(checks).getByText("Fix")).toBeInTheDocument();
    expect(within(checks).getByText(/Trail guide/)).toBeInTheDocument();
    expect(screen.getByText(/AI Overview does not cite you/)).toBeInTheDocument();
    expect(screen.getByText("blocked by robots.txt")).toBeInTheDocument();
    expect(screen.getByText("cushioning")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Suggest/ }));
    expect(
      await screen.findByText("AI suggestions aren't configured on this server."),
    ).toBeInTheDocument();
  });

  it("starts an analysis and hides write actions from viewers", async () => {
    let body: unknown = null;
    server.use(
      http.post("*/api/v1/orgs/:org/projects/:project/optimizer", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          {
            optimization: { ...summary, id: "o2", status: "running", score: null },
            job: {
              id: "j1",
              kind: "page_optimize",
              cancel_requested: false,
              status: "succeeded",
              progress: 1,
              stage: null,
              counters: {},
              result: {},
              error_code: null,
              error_message: null,
              project_id: PROJECT,
              created_at: "2026-09-24T00:00:00Z",
              started_at: null,
              finished_at: null,
            },
          },
          { status: 202 },
        );
      }),
    );
    renderPage();
    await userEvent.type(await screen.findByLabelText("Page URL"), "https://shop.com/trail");
    await userEvent.type(screen.getByLabelText("Target keyword"), "trail shoes");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    await vi.waitFor(() =>
      expect(body).toEqual({
        market_id: "m1",
        keyword: "trail shoes",
        url: "https://shop.com/trail",
      }),
    );
  });

  it("shows the keyword map and a Search Console prompt for cannibalization", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/keyword-map", () =>
        HttpResponse.json([
          {
            keyword_id: "k1",
            keyword: "trail shoes",
            market_id: "m1",
            target_url: "https://shop.com/trail",
            ranking_url: "https://shop.com/blog",
            ranking_source: "gsc",
            position: 7,
            status: "mismatch",
          },
        ]),
      ),
      http.get("*/api/v1/orgs/:org/projects/:project/cannibalization", () =>
        HttpResponse.json({ has_search_console_data: false, window_days: 28, issues: [] }),
      ),
    );
    renderPage("viewer");
    await screen.findByLabelText("Score 42 out of 100");
    expect(screen.queryByRole("button", { name: "Analyze" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Keyword map" }));
    expect(await screen.findByText("Different page ranks")).toBeInTheDocument();
    expect(screen.queryByLabelText("Target page")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Cannibalization" }));
    expect(await screen.findByText("Search Console data needed")).toBeInTheDocument();
  });
});
