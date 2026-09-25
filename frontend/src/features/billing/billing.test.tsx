import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { Organization } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { StepUpProvider } from "@/features/security/step-up";
import { setCsrfToken } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

import { isStripeUrl } from "./api";
import { BillingPage } from "./billing-page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const ORG = "0192f1a4-1b2c-7d3e-8f40-123456789abc";
const org: Organization = {
  id: ORG,
  name: "A",
  slug: "a",
  plan_code: "free",
  require_mfa: false,
  created_at: "2026-09-01T00:00:00Z",
  role: "billing",
};
const limits = (projects: number) => ({
  projects,
  members: 2,
  tracked_keywords: 50,
  crawl_pages_per_month: 500,
  ai_prompts_per_month: 50,
  rank_check_interval_hours: 168,
  search_engines: ["google"],
  ai_engines: [],
});
const billing = (overrides: Record<string, unknown> = {}) => ({
  configured: true,
  plan: "free",
  addons: [],
  status: "none",
  current_period_end: null,
  cancel_at_period_end: false,
  grace_until: null,
  has_customer: false,
  plans: [
    { code: "free", name: "Free", purchasable: false, limits: limits(1) },
    { code: "pro", name: "Pro", purchasable: true, limits: limits(10) },
    { code: "agency", name: "Agency", purchasable: false, limits: limits(100) },
  ],
  addons_catalog: [
    { code: "engines_bing", name: "Bing, Yahoo & DuckDuckGo", purchasable: true },
    { code: "engines_regional", name: "Yandex, Baidu, Naver & Seznam", purchasable: false },
  ],
  usage: { projects: { used: 1, limit: 1 }, tracked_keywords: { used: 10, limit: 50 } },
  ...overrides,
});

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

function renderPage() {
  renderWithQuery(
    <OrgProvider org={org}>
      <StepUpProvider>
        <BillingPage />
      </StepUpProvider>
    </OrgProvider>,
  );
}

describe("BillingPage", () => {
  it("only trusts Stripe-hosted URLs", () => {
    expect(isStripeUrl("https://checkout.stripe.com/c/pay/1")).toBe(true);
    expect(isStripeUrl("https://evil.com/stripe.com")).toBe(false);
    expect(isStripeUrl("http://checkout.stripe.com/")).toBe(false);
    expect(isStripeUrl("https://stripe.com.evil.io/")).toBe(false);
  });

  it("shows usage and sends the chosen plan and add-ons to checkout", async () => {
    let body: unknown = null;
    server.use(
      http.get("*/api/v1/orgs/:org/billing", () => HttpResponse.json(billing())),
      http.post("*/api/v1/orgs/:org/billing/checkout", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ url: "https://evil.example/phish" });
      }),
    );
    renderPage();
    expect(await screen.findByText("Current plan: Free")).toBeInTheDocument();
    expect(screen.getByText("1 / 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Not available yet" })).toBeDisabled();
    await userEvent.click(screen.getByLabelText("Bing, Yahoo & DuckDuckGo"));
    await userEvent.click(screen.getByRole("button", { name: "Choose Pro" }));
    await vi.waitFor(() => expect(body).toEqual({ plan: "pro", addons: ["engines_bing"] }));
    // A non-Stripe URL is never followed.
    expect(await screen.findByText("Could not open checkout.")).toBeInTheDocument();
  });

  it("says when billing isn't configured and warns during dunning", async () => {
    server.use(
      http.get("*/api/v1/orgs/:org/billing", () =>
        HttpResponse.json(
          billing({
            configured: false,
            plan: "pro",
            status: "past_due",
            grace_until: "2026-10-01T00:00:00Z",
          }),
        ),
      ),
    );
    renderPage();
    expect(await screen.findByText("Billing isn't configured on this server")).toBeInTheDocument();
    expect(screen.getByText(/Your last payment failed/)).toBeInTheDocument();
    expect(screen.queryByText("Choose a plan")).not.toBeInTheDocument();
  });
});
