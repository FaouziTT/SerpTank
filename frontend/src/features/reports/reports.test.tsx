import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { NotificationBell } from "./notifications";
import { PresencePage } from "./presence-page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
}));

const ORG = "0192f1a4-1b2c-7d3e-8f40-123456789abc";
const PROJECT = "0192f1a4-0000-7000-8000-000000000001";
const org: Organization = {
  id: ORG,
  name: "A",
  slug: "a",
  plan_code: "pro",
  require_mfa: false,
  created_at: "2026-09-01T00:00:00Z",
  role: "owner",
};
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
      search_engines: ["google", "bing"],
      ai_engines: [],
    },
  ],
};
const presence = {
  market_id: "0192f1a4-0000-7000-8000-0000000000aa",
  generated_at: "2026-09-24T00:00:00Z",
  score: 42,
  score_parts: { classic: 0.42, ai: null, ai_weight: 0.2 },
  volumes_known: false,
  engines: [
    {
      engine: "google",
      keywords: 3,
      share_of_voice: 0.42,
      distribution: { top3: 2, top20: 1 },
      weight: 0.87,
    },
    { engine: "bing", keywords: 0, share_of_voice: null, distribution: {}, weight: 0.07 },
  ],
  gsc: {
    latest_date: "2026-09-23",
    current: { clicks: 1200, impressions: 50000, ctr: 0.024, position: 9.1 },
    previous: { clicks: 1000, impressions: 45000, ctr: 0.022, position: 9.8 },
    daily: [],
  },
  opportunities: [{ query: "trail shoes", impressions: 900, clicks: 4, position: 11.2 }],
  audit: null,
  vitals: null,
  ai: { engines: [], first_party: [] },
};

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
  http.get("*/api/v1/orgs/:org/projects/:project/presence", () => HttpResponse.json(presence)),
  http.get("*/api/v1/orgs/:org/projects/:project/exports", () => HttpResponse.json([])),
  http.get("*/api/v1/orgs/:org/projects/:project/alerts", () =>
    HttpResponse.json([
      {
        kind: "rank_drop",
        label: "Ranking drops on Google",
        threshold_meaning: "positions lost",
        configured: false,
        active: false,
        threshold: 3,
        email: false,
        last_evaluated_at: null,
      },
    ]),
  ),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

describe("PresencePage", () => {
  it("shows the score, deltas and honest blanks", async () => {
    renderWithQuery(
      <OrgProvider org={org}>
        <PresencePage projectId={PROJECT} />
      </OrgProvider>,
    );
    expect(await screen.findByText("42/100")).toBeInTheDocument();
    expect(screen.getByText("Classic search only (no AI citation data yet).")).toBeInTheDocument();
    expect(screen.getByText("+20% vs previous 28 days")).toBeInTheDocument();
    expect(screen.getByText("Run a site audit.")).toBeInTheDocument();
    const bing = screen.getByText("Bing").closest("tr")!;
    expect(within(bing).getByText("No data")).toBeInTheDocument();
    expect(screen.getByText(/every keyword counts equally/)).toBeInTheDocument();
    expect(screen.getByText("trail shoes")).toBeInTheDocument();
  });

  it("turns an alert on", async () => {
    let body: unknown = null;
    server.use(
      http.put("*/api/v1/orgs/:org/projects/:project/alerts/:kind", async ({ request, params }) => {
        body = { kind: params.kind, ...((await request.json()) as Record<string, unknown>) };
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderWithQuery(
      <OrgProvider org={org}>
        <PresencePage projectId={PROJECT} />
      </OrgProvider>,
    );
    await userEvent.click(await screen.findByLabelText("Ranking drops on Google on"));
    await vi.waitFor(() =>
      expect(body).toEqual({ kind: "rank_drop", active: true, email: false, threshold: 3 }),
    );
  });
});

describe("NotificationBell", () => {
  it("shows the unread count", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/notifications", () =>
        HttpResponse.json({
          unread: 2,
          items: [
            {
              id: "n1",
              project_id: null,
              kind: "rank_drop",
              title: "“shoes” fell from #4 to #14",
              body: "",
              link: "/orgs/x/projects/y/keywords",
              read_at: null,
              created_at: "2026-09-24T00:00:00Z",
            },
          ],
        }),
      ),
    );
    renderWithQuery(<NotificationBell orgId={ORG} />);
    expect(await screen.findByLabelText("Notifications, 2 unread")).toBeInTheDocument();
  });
});
