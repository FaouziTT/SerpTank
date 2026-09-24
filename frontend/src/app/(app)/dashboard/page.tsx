import type { Metadata } from "next";

import { EmptyState } from "@/components/ui/empty-state";
import { getSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const session = await getSession();
  const name = session?.user.full_name.split(" ")[0] ?? "";
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-semibold">Welcome{name ? `, ${name}` : ""}</h1>
      {session && session.memberships.length === 0 ? (
        <EmptyState
          title="No organization yet"
          description="Create an organization to add your first website and start tracking."
        />
      ) : (
        <p className="text-muted-foreground">
          Your organizations: {session?.memberships.map((m) => m.organization_name).join(", ")}
        </p>
      )}
    </div>
  );
}
