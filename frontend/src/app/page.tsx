import Link from "next/link";

import { Button } from "@/components/ui/button";

// Minimal public landing page; the full marketing site is built in Module 13.
export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">SerpTank</h1>
      <p className="text-muted-foreground text-lg">
        Rank higher on Google, extend your reach to every search engine, and get cited in
        AI-generated answers.
      </p>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/register">Create an account</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    </main>
  );
}
