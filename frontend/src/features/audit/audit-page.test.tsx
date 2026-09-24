import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import type { Crawl, IssueSummary, Job } from "./api";
import { AuditPage, detailText } from "./audit-page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
}));

const ORG = "0192f1a4-1b2c-7d3e-8f40-123456789abc";
const PROJECT = "0192f1a4-0000-7000-8000-000000000001";
const org = (role: Organization["role"]): Organization => ({
  id: ORG,
  name: "Acme",
  slug: "acme",
  plan_code: "pro",
  require_mfa: false,
  created_at: "2026-09-01T00:00:00Z",
  role,
});
const project: Project = {
  id: PROJECT,
  name: "Main site",
  primary_domain: "example.com",
  verified: true,
  verification_method: "dns",
  crawl_schedule: "off",
  created_at: "2026-09-02T00:00:00Z",
  markets: [],
};
const crawl: Crawl = {
  id: "c1",
  job_id: "j1",
  status: "completed",
  start_url: "https://example.com/",
  max_pages: 100,
  domain_verified: true,
  engines: ["google", "bing"],
  pages_fetched: 42,
  pages_discovered: 50,
  budget_exhausted: false,
  render_available: false,
  score: 81.5,
  issue_counts: {
    scores: { google: 81.5, bing: 77 },
    by_severity: { critical: 0, high: 3, medium: 5, low: 1, info: 0 },
  },
  created_at: "2026-09-20T10:00:00Z",
  finished_at: "2026-09-20T10:05:00Z",
};
const issue = (over: Partial<IssueSummary>): IssueSummary => ({
  rule_id: "broken_pages",
  title: "Linked pages return 4xx errors",
  category: "indexability",
  category_label: "Indexability",
  severity: "high",
  scope: "all",
  description: "These URLs are linked but broken.",
  fix: "Restore or redirect them.",
  reference: "https://developers.google.com/search",
  effort: 2,
  affected: 3,
  priority: 5,
  examples: [],
  ...over,
});
const doneJob: Job = {
  id: "j1",
  kind: "crawl",
  status: "succeeded",
  project_id: PROJECT,
  progress: 1,
  stage: "auditing",
  counters: {},
  result: {},
  error_code: null,
  error_message: null,
  cancel_requested: false,
  created_at: "2026-09-20T10:00:00Z",
  started_at: null,
  finished_at: null,
};
const usage = {
  pages_used_this_month: 42,
  pages_per_month: 50000,
  max_pages_next_crawl: 10000,
  domain_verified: true,
};

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
  http.get("*/api/v1/orgs/:org/projects/:project/crawls/usage", () => HttpResponse.json(usage)),
  http.get("*/api/v1/orgs/:org/jobs", () => HttpResponse.json([doneJob])),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

function renderPage(role: Organization["role"] = "owner") {
  return renderWithQuery(
    <OrgProvider org={org(role)}>
      <AuditPage projectId={PROJECT} />
    </OrgProvider>,
  );
}

describe("AuditPage", () => {
  it("shows an honest empty state before the first audit", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/crawls", () => HttpResponse.json([])),
    );
    renderPage("viewer");
    expect(await screen.findByText("No audit yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run audit/ })).not.toBeInTheDocument();
  });

  it("shows scores and issues, with an engine lens and expandable details", async () => {
    const engines: string[] = [];
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/crawls", () => HttpResponse.json([crawl])),
      http.get("*/api/v1/orgs/:org/projects/:project/crawls/:crawl/issues", ({ request }) => {
        const engine = new URL(request.url).searchParams.get("engine") ?? "";
        engines.push(engine);
        const list = [issue({})];
        if (engine === "bing") {
          list.push(
            issue({
              rule_id: "bing_blocked_pages",
              title: "Blocked for Bingbot",
              scope: "bing",
              category: "engines",
              category_label: "Other search engines",
            }),
          );
        }
        return HttpResponse.json(list);
      }),
      http.get("*/api/v1/orgs/:org/projects/:project/crawls/:crawl/issues/:rule", () =>
        HttpResponse.json({
          rule_id: "broken_pages",
          total: 1,
          items: [
            {
              url: "https://example.com/gone",
              details: { status: 404, linked_from: ["https://example.com/"] },
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText("82")).toBeInTheDocument(); // Google score, rounded
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText(/renderer unavailable/)).toBeInTheDocument();
    const row = await screen.findByRole("button", { name: /Linked pages return 4xx errors/ });
    await user.click(row);
    expect(await screen.findByText("https://example.com/gone")).toBeInTheDocument();
    expect(screen.getByText(/status: 404/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Documentation/ })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );

    await user.click(screen.getByRole("tab", { name: "Bing" }));
    expect(await screen.findByText("Blocked for Bingbot")).toBeInTheDocument();
    expect(screen.getByText("Bing only")).toBeInTheDocument();
    expect(screen.getByText("77")).toBeInTheDocument();
    expect(engines).toEqual(["google", "bing"]);
  });

  it("starts an audit and follows progress until it finishes", async () => {
    let polls = 0;
    const running: Job = { ...doneJob, id: "j2", status: "queued", progress: 0, stage: null };
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/crawls", () => HttpResponse.json([])),
      http.get("*/api/v1/orgs/:org/jobs", () => HttpResponse.json([])),
      http.post("*/api/v1/orgs/:org/projects/:project/crawls", () =>
        HttpResponse.json({ job: running, pages_budget: 10000 }, { status: 202 }),
      ),
      http.get("*/api/v1/orgs/:org/jobs/:job", () => {
        polls += 1;
        return HttpResponse.json(
          polls < 2
            ? {
                ...running,
                status: "running",
                progress: 0.4,
                stage: "crawling",
                counters: { pages_fetched: 40, max_pages: 100 },
              }
            : {
                ...running,
                status: "failed",
                error_message: "Your robots.txt could not be fetched.",
              },
        );
      }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Run audit/ }));
    const status = await screen.findByRole("status");
    await waitFor(() => expect(within(status).getByText("Crawling pages")).toBeInTheDocument(), {
      timeout: 5000,
    });
    expect(within(status).getByText("40 of up to 100 pages")).toBeInTheDocument();
    expect(
      await screen.findByText(/robots.txt could not be fetched/, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  }, 15000);
});

describe("detailText", () => {
  it("renders details as plain text", () => {
    expect(detailText({ hops: 2, final_url: "https://x/", list: ["a", { b: 1 }] })).toBe(
      'hops: 2 · final url: https://x/ · list: a, {"b":1}',
    );
    expect(detailText({ html: "<script>alert(1)</script>" })).toContain("<script>");
  });
});
