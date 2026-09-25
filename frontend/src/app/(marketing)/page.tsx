import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: { absolute: "SerpTank: Google-first SEO and AI search visibility" },
  description:
    "Technical audits, rank tracking, keyword research and content optimisation built on Google's own guidance, plus visibility in AI Overviews, ChatGPT and Perplexity.",
  alternates: { canonical: "/" },
};

// Every claim below describes a feature that exists in the product. No invented
// customers, testimonials or statistics (plan §6.2, M13).
const TRACKS = [
  {
    title: "Classic search, Google first",
    points: [
      "Site audits built on Google Search Essentials, with JavaScript rendering checks and Core Web Vitals field data",
      "Search Console, Analytics and Bing Webmaster Tools data, synced daily into your own history",
      "Rank tracking that uses your first-party positions for free and live checks for competitors and SERP features",
      "Keyword research, intent, difficulty and striking-distance opportunities",
      "Bing, Yahoo, DuckDuckGo, Yandex, Baidu, Naver and Seznam as plan add-ons",
    ],
  },
  {
    title: "AI search visibility",
    points: [
      "See when Google AI Overviews, ChatGPT and Perplexity mention or cite you, with confidence ranges instead of single-run guesses",
      "Share of voice against your competitors across AI answers",
      "A readiness score based on the fundamentals that let AI search find and cite you",
      "Import Search Console's Gen-AI report and Bing's AI Performance data",
    ],
  },
];
const PRINCIPLES = [
  [
    "Your data, not estimates",
    "When data isn't available we say so. We never fill gaps with made-up numbers.",
  ],
  ["Explainable", "Every score comes with the checks behind it and what to do next."],
  [
    "Secure by design",
    "Tenant isolation in the database, cookie-only sessions, MFA and passkeys, and every outbound request through an SSRF-safe client.",
  ],
] as const;

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-16 px-6 py-16">
      <section className="space-y-6 text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          Rank on Google. Get cited by AI.
        </h1>
        <p className="text-muted-foreground mx-auto max-w-2xl text-lg">
          SerpTank brings technical SEO, rankings, content and AI-search visibility together,
          measured against what actually ranks, from your own first-party data.
        </p>
        <div className="flex justify-center gap-3">
          <Button asChild size="lg">
            <Link href="/register">Start free</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/pricing">See plans</Link>
          </Button>
        </div>
      </section>
      <section className="grid gap-8 md:grid-cols-2" aria-label="What SerpTank does">
        {TRACKS.map((track) => (
          <div key={track.title} className="space-y-3 rounded-lg border p-6">
            <h2 className="text-xl font-semibold">{track.title}</h2>
            <ul className="text-muted-foreground list-disc space-y-2 pl-5 text-sm">
              {track.points.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>
      <section className="grid gap-6 md:grid-cols-3" aria-label="How we work">
        {PRINCIPLES.map(([title, text]) => (
          <div key={title} className="space-y-1">
            <h2 className="font-semibold">{title}</h2>
            <p className="text-muted-foreground text-sm">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
