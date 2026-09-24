import type { Metadata } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "SerpTank", template: "%s · SerpTank" },
  description: "Google-first SEO and AI-search visibility platform.",
  robots: { index: false, follow: false },
  icons: { icon: "/favicon-32.svg" },
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Reading request headers opts every page into dynamic rendering, which the
  // per-request CSP nonce (set in proxy.ts) requires. Next applies the nonce itself.
  await headers();
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
