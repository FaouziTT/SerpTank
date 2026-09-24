import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization, Project } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { IntegrationsPage } from "./integrations-page";
import { SearchDataPage } from "./search-data-page";

let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => search,
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
  name: "Shop",
  primary_domain: "shop.com",
  verified: true,
  verification_method: "gsc",
  crawl_schedule: "off",
  created_at: "2026-09-02T00:00:00Z",
  markets: [],
};

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "csrf-1" })),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
  search = new URLSearchParams();
});
afterAll(() => server.close());

describe("IntegrationsPage", () => {
  it("starts the Google OAuth flow with the chosen permissions", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, origin: window.location.origin });
    let requested: unknown = null;
    server.use(
      http.get("*/api/v1/orgs/:org/integrations", () =>
        HttpResponse.json({
          connections: [],
          google_available: true,
          vitals_available: true,
          keyword_planner_available: false,
        }),
      ),
      http.post("*/api/v1/orgs/:org/integrations/google/start", async ({ request }) => {
        requested = await request.json();
        return HttpResponse.json({
          authorization_url: "https://accounts.google.com/o/oauth2/v2/auth?x=1",
        });
      }),
    );
    const user = userEvent.setup();
    renderWithQuery(
      <OrgProvider org={org("admin")}>
        <IntegrationsPage />
      </OrgProvider>,
    );
    await user.click(await screen.findByLabelText(/Submit sitemaps/));
    await user.click(screen.getByRole("button", { name: /Connect Google/ }));
    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith("https://accounts.google.com/o/oauth2/v2/auth?x=1"),
    );
    expect(requested).toEqual({ features: ["gsc", "ga4", "gsc_write"] });
    vi.unstubAllGlobals();
  });

  it("explains callback errors and hides controls from viewers", async () => {
    search = new URLSearchParams("error=google_state_invalid");
    server.use(
      http.get("*/api/v1/orgs/:org/integrations", () =>
        HttpResponse.json({
          connections: [
            {
              provider: "google",
              status: "reauth_required",
              account_label: "a@b.co",
              scopes: [],
              features: ["gsc"],
              last_error_code: "x",
              created_at: "2026-09-01T00:00:00Z",
              settings: {},
            },
          ],
          google_available: true,
          vitals_available: false,
          keyword_planner_available: false,
        }),
      ),
    );
    renderWithQuery(
      <OrgProvider org={org("viewer")}>
        <IntegrationsPage />
      </OrgProvider>,
    );
    expect(await screen.findByText(/expired or was started by someone else/)).toBeInTheDocument();
    expect(screen.getByText("Reconnect needed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Connect Google/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Not configured on this server/)).toBeInTheDocument();
  });
});

describe("SearchDataPage", () => {
  it("shows honest empty states and uploads CSV exports as text/csv", async () => {
    let upload: { type: string | null; csrf: string | null; body: string } | null = null;
    server.use(
      http.get("*/api/v1/orgs/:org/projects/:project", () => HttpResponse.json(project)),
      http.get("*/api/v1/orgs/:org/projects/:project/sources", () =>
        HttpResponse.json([
          {
            id: "s1",
            kind: "indexnow",
            property_id: "abcdef123456",
            settings: { verified: false },
            last_sync_at: null,
            last_sync_status: null,
            synced_through: null,
          },
        ]),
      ),
      http.get("*/api/v1/orgs/:org/integrations/google/properties", () =>
        HttpResponse.json({
          gsc_sites: [{ id: "sc-domain:shop.com", label: "sc-domain:shop.com (siteOwner)" }],
          ga4_properties: [],
        }),
      ),
      http.get("*/api/v1/orgs/:org/integrations/bing/sites", () =>
        HttpResponse.json(
          { type: "x", title: "Not connected", status: 404, code: "not_found" },
          { status: 404 },
        ),
      ),
      http.get("*/api/v1/orgs/:org/projects/:project/performance", () =>
        HttpResponse.json({
          source: "gsc",
          days: 28,
          date_from: "2026-08-28",
          date_to: "2026-09-24",
          has_data: false,
          clicks: 0,
          impressions: 0,
          ctr: null,
          position: null,
          top_queries: [],
          top_pages: [],
        }),
      ),
      http.get("*/api/v1/orgs/:org/projects/:project/vitals", () => HttpResponse.json([])),
      http.get("*/api/v1/orgs/:org/projects/:project/ai-performance", () => HttpResponse.json([])),
      http.get("*/api/v1/orgs/:org/projects/:project/submissions", () => HttpResponse.json([])),
      http.post("*/api/v1/orgs/:org/projects/:project/imports/:source", async ({ request }) => {
        upload = {
          type: request.headers.get("content-type"),
          csrf: request.headers.get("x-csrf-token"),
          body: await request.text(),
        };
        return HttpResponse.json({
          rows: 2,
          bad_rows: 0,
          errors: [],
          date_from: "2026-09-01",
          date_to: "2026-09-02",
          columns: {},
          missing_metrics: [],
        });
      }),
    );
    const user = userEvent.setup();
    renderWithQuery(
      <OrgProvider org={org("owner")}>
        <SearchDataPage projectId={PROJECT} />
      </OrgProvider>,
    );
    expect(await screen.findByText("No data yet")).toBeInTheDocument();
    expect(screen.getByText(/No field data yet/)).toBeInTheDocument();
    expect(screen.getByText("Key file not found yet")).toBeInTheDocument();
    expect(screen.getByText("https://shop.com/abcdef123456.txt")).toBeInTheDocument();
    // Bing isn't connected: a pointer to the Integrations page instead of a dead select.
    expect(await screen.findByRole("link", { name: "Integrations" })).toBeInTheDocument();

    const file = new File(["Date,Impressions\n2026-09-01,5\n"], "genai.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("CSV file"), file);
    await user.click(screen.getByRole("button", { name: "Import CSV" }));
    expect(await screen.findByText(/Imported 2 rows/)).toBeInTheDocument();
    expect(upload).toEqual({
      type: "text/csv",
      csrf: "csrf-1",
      body: "Date,Impressions\n2026-09-01,5\n",
    });
  });
});
