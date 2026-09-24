import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="bg-muted/40 flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <Link href="/" className="block text-center text-2xl font-semibold tracking-tight">
          SerpTank
        </Link>
        {children}
      </div>
    </main>
  );
}
