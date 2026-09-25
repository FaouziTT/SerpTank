"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { FormAlert } from "@/components/forms/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { errorText } from "@/features/orgs/errors";
import { useOrg } from "@/features/orgs/org-context";
import { useStepUp } from "@/features/security/step-up";

import { billingApi, billingKeys, isStripeUrl, type CheckoutRequest } from "./api";

type Addon = NonNullable<CheckoutRequest["addons"]>[number];

const num = new Intl.NumberFormat();
const METERS: [string, string][] = [
  ["projects", "Projects"],
  ["members", "Members"],
  ["tracked_keywords", "Tracked keywords"],
  ["crawl_pages_this_month", "Crawled pages this month"],
  ["serp_requests_today", "Live SERP checks today"],
  ["ai_samples_this_month", "AI answer samples this month"],
  ["llm_tokens_this_month", "AI tokens this month"],
];
const STATUS: Record<string, string> = {
  none: "No subscription",
  active: "Active",
  trialing: "Trial",
  past_due: "Payment failed",
  canceled: "Canceled",
  unpaid: "Unpaid",
  incomplete: "Incomplete",
};

function go(url: string) {
  if (!isStripeUrl(url)) throw new Error("Unexpected payment page.");
  window.location.assign(url);
}

export function BillingPage() {
  const org = useOrg();
  const stepUp = useStepUp();
  const params = useSearchParams();
  const billing = useQuery({
    queryKey: billingKeys.all(org.id),
    queryFn: () => billingApi.get(org.id),
  });
  const invoices = useQuery({
    queryKey: [...billingKeys.all(org.id), "invoices"],
    queryFn: () => billingApi.invoices(org.id),
    enabled: Boolean(billing.data?.configured && billing.data.has_customer),
  });
  const [addons, setAddons] = useState<Addon[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (billing.isPending) return <Skeleton className="h-64" />;
  if (billing.isError) return <ErrorState error={billing.error} />;
  const data = billing.data;
  const live = ["active", "trialing", "past_due"].includes(data.status);

  async function checkout(plan: CheckoutRequest["plan"]) {
    setError(null);
    setBusy(true);
    try {
      const { url } = await stepUp(() => billingApi.checkout(org.id, { plan, addons }));
      go(url);
    } catch (err) {
      setError(errorText(err, "Could not open checkout."));
      setBusy(false);
    }
  }

  async function portal() {
    setError(null);
    setBusy(true);
    try {
      go((await billingApi.portal(org.id)).url);
    } catch (err) {
      setError(errorText(err, "Could not open the billing portal."));
      setBusy(false);
    }
  }

  return (
    <div className="max-w-5xl space-y-6">
      <h1 className="text-2xl font-semibold">Billing</h1>
      {params.get("checkout") === "success" ? (
        <p role="status" className="rounded-md border p-3 text-sm">
          Thanks! Your plan updates as soon as Stripe confirms the payment (usually seconds).
        </p>
      ) : null}
      <FormAlert message={error} />
      {!data.configured ? (
        <EmptyState
          title="Billing isn't configured on this server"
          description="Plans can't be purchased here yet. Your current plan and usage are shown below."
        />
      ) : null}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Current plan: {data.plans.find((p) => p.code === data.plan)?.name ?? data.plan}
          </CardTitle>
          <CardDescription>
            {STATUS[data.status] ?? data.status}
            {data.current_period_end
              ? ` · ${data.cancel_at_period_end ? "ends" : "renews"} ${new Date(data.current_period_end).toLocaleDateString()}`
              : ""}
            {data.addons.length ? ` · add-ons: ${data.addons.join(", ")}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {data.status === "past_due" && data.grace_until ? (
            <FormAlert
              message={`Your last payment failed. Paid features stay on until ${new Date(data.grace_until).toLocaleDateString()}; update your card in Manage billing.`}
            />
          ) : null}
          <ul className="grid gap-2 sm:grid-cols-2" aria-label="Usage">
            {METERS.map(([key, label]) => {
              const meter = data.usage[key];
              if (!meter) return null;
              const share = meter.limit ? Math.min(1, meter.used / meter.limit) : 0;
              return (
                <li key={key} className="text-sm">
                  <div className="flex justify-between">
                    <span>{label}</span>
                    <span className="text-muted-foreground">
                      {num.format(meter.used)} / {num.format(meter.limit)}
                    </span>
                  </div>
                  <div className="bg-muted mt-1 h-1.5 rounded" aria-hidden>
                    <div
                      className={`h-1.5 rounded ${share >= 0.9 ? "bg-destructive" : "bg-primary"}`}
                      style={{ width: `${Math.round(share * 100)}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
          {data.configured && data.has_customer ? (
            <Button variant="outline" disabled={busy} onClick={() => void portal()}>
              Manage billing
            </Button>
          ) : null}
        </CardContent>
      </Card>
      {data.configured && !live ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Choose a plan</CardTitle>
            <CardDescription>
              Google and AI visibility are in every plan. Payment is handled by Stripe.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <fieldset className="space-y-1">
              <legend className="text-sm font-medium">Engine add-ons</legend>
              {data.addons_catalog.map((a) => (
                <label key={String(a.code)} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={!a.purchasable}
                    checked={addons.includes(a.code as Addon)}
                    onChange={(e) => {
                      const code = a.code as Addon;
                      setAddons((prev) =>
                        e.target.checked ? [...prev, code] : prev.filter((c) => c !== code),
                      );
                    }}
                  />
                  {String(a.name)}
                </label>
              ))}
            </fieldset>
            <div className="grid gap-3 md:grid-cols-2">
              {data.plans
                .filter((p) => p.code !== "free")
                .map((p) => (
                  <div key={p.code} className="space-y-2 rounded-md border p-3 text-sm">
                    <p className="font-medium">{p.name}</p>
                    <ul className="text-muted-foreground text-xs">
                      <li>{num.format(Number(p.limits.projects))} projects</li>
                      <li>{num.format(Number(p.limits.tracked_keywords))} tracked keywords</li>
                      <li>
                        {num.format(Number(p.limits.crawl_pages_per_month))} crawled pages / month
                      </li>
                      <li>
                        {num.format(Number(p.limits.ai_prompts_per_month))} AI samples / month
                      </li>
                    </ul>
                    <Button
                      size="sm"
                      disabled={busy || !p.purchasable}
                      onClick={() => void checkout(p.code as CheckoutRequest["plan"])}
                    >
                      {p.purchasable ? `Choose ${p.name}` : "Not available yet"}
                    </Button>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      ) : null}
      {invoices.data && invoices.data.length > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Invoices</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Number</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.data.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>
                      {i.hosted_invoice_url ? (
                        <a
                          href={i.hosted_invoice_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="underline"
                        >
                          {i.number ?? i.id}
                        </a>
                      ) : (
                        (i.number ?? i.id)
                      )}
                    </TableCell>
                    <TableCell>{new Date(i.created).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{i.status ?? "—"}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {new Intl.NumberFormat(undefined, {
                        style: "currency",
                        currency: i.currency.toUpperCase() || "USD",
                      }).format(i.total / 100)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
