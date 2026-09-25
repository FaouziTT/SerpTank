import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { publicPricing } from "@/features/marketing/site";

export const metadata: Metadata = {
  title: "Pricing",
  description: "SerpTank plans: Google and AI visibility in every plan, other engines as add-ons.",
  alternates: { canonical: "/pricing" },
};

const ENGINE: Record<string, string> = {
  google: "Google",
  bing: "Bing",
  yahoo: "Yahoo",
  duckduckgo: "DuckDuckGo",
  yandex: "Yandex",
  baidu: "Baidu",
  naver: "Naver",
  seznam: "Seznam",
};

export default async function PricingPage() {
  const pricing = await publicPricing();
  if (!pricing) {
    return (
      <p className="mx-auto max-w-3xl px-6 py-16">
        Pricing is unavailable right now. Please try again later.
      </p>
    );
  }
  const num = new Intl.NumberFormat("en");
  const money = (value: number, currency: string) =>
    new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 0 }).format(
      value,
    );
  return (
    <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
      <header className="space-y-2 text-center">
        <h1 className="text-4xl font-semibold">Pricing</h1>
        <p className="text-muted-foreground">
          Google and AI-search visibility are in every plan. Add other engines when you need them.
        </p>
      </header>
      <div className="grid gap-6 md:grid-cols-3">
        {pricing.plans.map((plan) => {
          const limits = plan.limits as Record<string, number | string[]>;
          return (
            <section
              key={plan.code}
              className="flex flex-col gap-4 rounded-lg border p-6"
              aria-label={plan.name}
            >
              <h2 className="text-xl font-semibold">{plan.name}</h2>
              <p className="text-3xl font-semibold">
                {plan.monthly_price === null ? (
                  <span className="text-muted-foreground text-base font-normal">
                    Price shown at checkout
                  </span>
                ) : plan.monthly_price === 0 ? (
                  "Free"
                ) : (
                  <>
                    {money(plan.monthly_price, plan.currency)}
                    <span className="text-muted-foreground text-base font-normal">/month</span>
                  </>
                )}
              </p>
              <ul className="text-muted-foreground flex-1 space-y-1 text-sm">
                <li>{num.format(limits.projects as number)} projects</li>
                <li>{num.format(limits.members as number)} team members</li>
                <li>{num.format(limits.tracked_keywords as number)} tracked keywords</li>
                <li>{num.format(limits.crawl_pages_per_month as number)} audited pages / month</li>
                <li>
                  {num.format(limits.ai_prompts_per_month as number)} AI answer samples / month
                </li>
                <li>
                  Rankings refreshed every{" "}
                  {(limits.rank_check_interval_hours as number) >= 168 ? "week" : "day"}
                </li>
                <li>
                  Engines:{" "}
                  {(limits.search_engines as string[]).map((e) => ENGINE[e] ?? e).join(", ")}
                </li>
              </ul>
              <Button asChild variant={plan.code === "pro" ? "default" : "outline"}>
                <Link href="/register">
                  {plan.code === "free" ? "Start free" : `Start with ${plan.name}`}
                </Link>
              </Button>
            </section>
          );
        })}
      </div>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Engine add-ons</h2>
        <ul className="text-sm">
          {pricing.addons.map((a) => (
            <li key={String(a.code)}>
              {String(a.name)}:{" "}
              {typeof a.monthly_price === "number"
                ? `${money(a.monthly_price, pricing.plans[0]?.currency ?? "USD")}/month`
                : "price shown at checkout"}
            </li>
          ))}
        </ul>
        <p className="text-muted-foreground text-xs">
          Prices exclude applicable taxes. Payment is handled by Stripe; the amount at checkout is
          final.
        </p>
      </section>
    </div>
  );
}
