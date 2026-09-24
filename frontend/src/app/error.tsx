"use client";

// Error boundary: shows a generic message and the trace id if the API provided one.
// Error details are never rendered (they may contain internals).
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="text-muted-foreground">
        Please try again. If the problem persists, contact support.
      </p>
      <button className="text-primary underline-offset-4 hover:underline" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
