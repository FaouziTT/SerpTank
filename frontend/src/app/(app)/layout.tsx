import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { getSession } from "@/lib/api/server";

// Authoritative authentication gate: every page under (app) is rendered only after the
// backend confirms a fully authenticated (MFA-complete) session for this request.
export default async function AppLayout({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/login");
  return <AppShell session={session}>{children}</AppShell>;
}
