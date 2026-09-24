import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { KeywordsPage } from "./keywords-page";

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

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

describe("KeywordsPage", () => {
  it("shows first-party and live positions per engine, Google first", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/keywords", () =>
        HttpResponse.json([
          {
            id: "k1",
            keyword: "best running shoes",
            market_id: "m1",
            tags: [],
            intent: "commercial",
            volume: 90500,
            volume_source: "google_ads",
            positions: [
              {
                engine: "google",
                source: "gsc",
                position: 4.5,
                previous: 6,
                date: "2026-09-20",
                url: null,
                features: [],
                ai_cited: null,
              },
              {
                engine: "google",
                source: "serp",
                position: 2,
                previous: 1,
                date: "2026-09-24",
                url: null,
                features: ["ai_overview"],
                ai_cited: true,
              },
              {
                engine: "bing",
                source: "serp",
                position: null,
                previous: null,
                date: "2026-09-24",
                url: null,
                features: [],
                ai_cited: null,
              },
            ],
          },
        ]),
      ),
    );
    renderWithQuery(
      <OrgProvider org={org}>
        <KeywordsPage projectId={PROJECT} />
      </OrgProvider>,
    );
    const row = (await screen.findByText("best running shoes")).closest("tr")!;
    expect(within(row).getByText("90,500")).toBeInTheDocument();
    expect(within(row).getByText("Search Console")).toBeInTheDocument();
    expect(within(row).getByLabelText("up 1.5")).toBeInTheDocument();
    expect(within(row).getByLabelText("down 1")).toBeInTheDocument();
    expect(within(row).getByText("AI cited")).toBeInTheDocument();
    expect(within(row).getByText(">100")).toBeInTheDocument(); // honest "not in the checked depth"
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers.indexOf("Google")).toBeLessThan(headers.indexOf("Bing"));
  });

  it("explains when no research source is connected and when opportunities need GSC", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project/keywords", () => HttpResponse.json([])),
      http.post("*/api/v1/orgs/:org/projects/:project/keywords/research", () =>
        HttpResponse.json(
          {
            type: "x",
            title: "Conflict",
            status: 409,
            code: "conflict",
            detail:
              "Connect Google Ads (Keyword Planner) or Bing Webmaster Tools to research keywords.",
          },
          { status: 409, headers: { "content-type": "application/problem+json" } },
        ),
      ),
      http.get("*/api/v1/orgs/:org/projects/:project/keywords/opportunities", () =>
        HttpResponse.json({
          has_data: false,
          curve_source: "default",
          date_from: null,
          date_to: null,
          items: [],
        }),
      ),
    );
    const user = userEvent.setup();
    renderWithQuery(
      <OrgProvider org={org}>
        <KeywordsPage projectId={PROJECT} />
      </OrgProvider>,
    );
    expect(await screen.findByText("No keywords tracked")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Research" }));
    await user.type(screen.getByLabelText("Seed keyword"), "running shoes");
    await user.click(screen.getByRole("button", { name: "Find ideas" }));
    expect(await screen.findByText(/Connect Google Ads/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Opportunities" }));
    expect(await screen.findByText("Connect Search Console")).toBeInTheDocument();
  });
});
