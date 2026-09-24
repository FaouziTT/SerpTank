import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { StepUpProvider } from "@/features/security/step-up";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { AcceptInvite } from "./accept-invite";
import type { Entitlements, Organization, Project } from "./api";
import { MarketFields, DEFAULT_MARKET } from "./market-fields";
import { OrgProvider } from "./org-context";
import { OrgOverview } from "./org-overview";
import { OrgSettings } from "./org-settings";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/orgs/x",
}));

const ORG_ID = "0192f1a4-1b2c-7d3e-8f40-123456789abc";
const org = (role: Organization["role"]): Organization => ({
  id: ORG_ID,
  name: "Acme",
  slug: "acme",
  plan_code: "free",
  require_mfa: false,
  created_at: "2026-09-01T00:00:00Z",
  role,
});
const FREE: Entitlements = {
  plan_code: "free",
  plan_name: "Free",
  search_engines: ["google"],
  ai_engines: ["google_ai_overview", "google_ai_mode"],
  max_projects: 1,
  max_markets_per_project: 1,
  max_members: 2,
  max_tracked_keywords: 100,
  max_crawl_pages_per_month: 1000,
  ai_prompts_per_month: 50,
  rank_check_interval_hours: 168,
};
const PROJECT: Project = {
  id: "0192f1a4-0000-7000-8000-000000000001",
  name: "Main site",
  primary_domain: "example.com",
  verified: false,
  verification_method: null,
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

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
  http.get("*/api/v1/orgs/:id/entitlements", () => HttpResponse.json(FREE)),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
  push.mockReset();
});
afterAll(() => server.close());

describe("OrgOverview", () => {
  it("shows an honest empty state for a new org", async () => {
    server.use(http.get("*/api/v1/orgs/:id/projects", () => HttpResponse.json([])));
    renderWithQuery(
      <OrgProvider org={org("owner")}>
        <OrgOverview />
      </OrgProvider>,
    );
    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add a website" })).toBeInTheDocument();
  });

  it("lists projects and blocks creation at the plan limit", async () => {
    server.use(http.get("*/api/v1/orgs/:id/projects", () => HttpResponse.json([PROJECT])));
    renderWithQuery(
      <OrgProvider org={org("owner")}>
        <OrgOverview />
      </OrgProvider>,
    );
    expect(await screen.findByText("Main site")).toBeInTheDocument();
    expect(screen.getByText("Unverified")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /New project/ })).toBeDisabled());
    expect(screen.getByText(/reached your plan's project limit/)).toBeInTheDocument();
  });

  it("hides write controls from viewers", async () => {
    server.use(http.get("*/api/v1/orgs/:id/projects", () => HttpResponse.json([])));
    renderWithQuery(
      <OrgProvider org={org("viewer")}>
        <OrgOverview />
      </OrgProvider>,
    );
    expect(await screen.findByText(/No websites have been added/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /New project/ })).not.toBeInTheDocument();
  });
});

describe("MarketFields", () => {
  it("locks engines that the plan does not include", () => {
    renderWithQuery(
      <MarketFields idPrefix="t" value={DEFAULT_MARKET} onChange={() => {}} entitlements={FREE} />,
    );
    expect(screen.getByRole("checkbox", { name: /Google$/ })).toBeEnabled();
    expect(screen.getByRole("checkbox", { name: /Bing/ })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: /Yandex/ })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: /Google AI Overviews/ })).toBeEnabled();
    expect(screen.getByRole("checkbox", { name: /ChatGPT/ })).toBeDisabled();
  });
});

describe("AcceptInvite", () => {
  it("shows the API's reason when the invitation is for another address", async () => {
    server.use(
      http.post("*/api/v1/invitations/accept", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Forbidden",
            status: 403,
            detail: "This invitation was sent to a different email address.",
            code: "permission_denied",
          },
          { status: 403, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    renderWithQuery(<AcceptInvite token="tok" email="ana@example.com" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Accept invitation" }));
    expect(await screen.findByText(/different email address/)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("joins and navigates to the organization", async () => {
    server.use(http.post("*/api/v1/invitations/accept", () => HttpResponse.json(org("editor"))));
    renderWithQuery(<AcceptInvite token="tok" email="ana@example.com" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Accept invitation" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith(`/orgs/${ORG_ID}`));
  });

  it("explains an incomplete link", () => {
    renderWithQuery(<AcceptInvite token={null} email="ana@example.com" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/incomplete/);
  });
});

describe("OrgSettings API keys", () => {
  it("steps up, then shows the new key exactly once", async () => {
    let attempts = 0;
    let keys: unknown[] = [];
    server.use(
      http.get("*/api/v1/orgs/:id/api-keys", () => HttpResponse.json(keys)),
      http.post("*/api/v1/orgs/:id/api-keys", () => {
        attempts += 1;
        if (attempts === 1) {
          return HttpResponse.json(
            {
              type: "x",
              title: "Re-authentication required",
              status: 403,
              code: "reauth_required",
            },
            { status: 403, headers: { "content-type": "application/problem+json" } },
          );
        }
        const record = {
          id: "k1",
          name: "CI",
          prefix: "abcd1234",
          scopes: ["read"],
          created_at: "2026-09-24T00:00:00Z",
          expires_at: null,
          last_used_at: null,
          revoked_at: null,
        };
        keys = [record];
        return HttpResponse.json({ ...record, key: "stk_live_abcd1234_secret" }, { status: 201 });
      }),
      http.post("*/api/v1/auth/reauth", () => HttpResponse.json({ csrf_token: "t2" })),
    );
    const user = userEvent.setup();
    renderWithQuery(
      <OrgProvider org={org("admin")}>
        <StepUpProvider>
          <OrgSettings />
        </StepUpProvider>
      </OrgProvider>,
    );
    await user.type(await screen.findByLabelText("Key name"), "CI");
    await user.click(screen.getByRole("button", { name: "Create key" }));
    await user.type(
      await screen.findByLabelText("Password or authentication code"),
      "pw pw pw pw pw",
    );
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("stk_live_abcd1234_secret")).toBeInTheDocument();
    expect(await screen.findByText(/stk_live_abcd1234_…/)).toBeInTheDocument();
    expect(attempts).toBe(2);
    // Admins cannot delete the organization.
    expect(screen.queryByText("Delete organization")).not.toBeInTheDocument();
  });
});
