/** Typed wrappers for billing (Stripe Checkout / Portal, invoices, usage). */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type Billing = S["BillingOut"];
export type Invoice = S["InvoiceOut"];
export type CheckoutRequest = S["CheckoutRequest"];

const org = (org_id: string) => ({ params: { path: { org_id } } });

export const billingKeys = { all: (orgId: string) => ["orgs", orgId, "billing"] };

export const billingApi = {
  get: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/billing", org(orgId))),
  invoices: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/billing/invoices", org(orgId))),
  checkout: (orgId: string, body: CheckoutRequest) =>
    unwrap(api.POST("/api/v1/orgs/{org_id}/billing/checkout", { ...org(orgId), body })),
  portal: (orgId: string) => unwrap(api.POST("/api/v1/orgs/{org_id}/billing/portal", org(orgId))),
};

/** Only ever navigate to Stripe-hosted pages returned by our API. */
export function isStripeUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname;
    return (
      new URL(url).protocol === "https:" && (host === "stripe.com" || host.endsWith(".stripe.com"))
    );
  } catch {
    return false;
  }
}
