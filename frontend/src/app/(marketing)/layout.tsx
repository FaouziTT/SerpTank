import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { siteUrl } from "@/features/marketing/site";

export function generateMetadata(): Metadata {
  return {
    metadataBase: new URL(siteUrl()),
    // The public site is indexable; the app (root default) is not.
    robots: { index: true, follow: true },
    openGraph: { siteName: "SerpTank", type: "website" },
  };
}

const NAV = [
  ["/pricing", "Pricing"],
  ["/security", "Security"],
] as const;
const FOOTER = [
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
  ["/dpa", "DPA"],
  ["/subprocessors", "Subprocessors"],
  ["/security", "Security"],
] as const;

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <Link href="/" className="font-semibold">
            SerpTank
          </Link>
          <nav aria-label="Main" className="flex items-center gap-4 text-sm">
            {NAV.map(([href, label]) => (
              <Link key={href} href={href} className="hover:underline">
                {label}
              </Link>
            ))}
            <Button asChild size="sm" variant="outline">
              <Link href="/login">Sign in</Link>
            </Button>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t">
        <nav
          aria-label="Legal"
          className="text-muted-foreground mx-auto flex max-w-5xl flex-wrap gap-4 px-6 py-6 text-sm"
        >
          {FOOTER.map(([href, label]) => (
            <Link key={href} href={href} className="hover:underline">
              {label}
            </Link>
          ))}
        </nav>
      </footer>
    </div>
  );
}
