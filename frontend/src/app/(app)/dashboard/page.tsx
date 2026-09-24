import { Building2, Plus } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ROLE_LABELS } from "@/features/orgs/permissions";
import { getSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Organizations" };

export default async function DashboardPage() {
  const session = await getSession();
  const name = session?.user.full_name.split(" ")[0] ?? "";
  const memberships = session?.memberships ?? [];
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Welcome{name ? `, ${name}` : ""}</h1>
        {memberships.length > 0 ? (
          <Button asChild variant="outline">
            <Link href="/orgs/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden /> New organization
            </Link>
          </Button>
        ) : null}
      </div>
      {memberships.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No organization yet"
          description="Create an organization to add your first website and start tracking. If a teammate invited you, open the link from their email."
          action={
            <Button asChild>
              <Link href="/orgs/new">Create organization</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {memberships.map((m) => (
            <Link key={m.organization_id} href={`/orgs/${m.organization_id}`}>
              <Card className="hover:border-primary/50 transition-colors">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between text-base">
                    {m.organization_name}
                    <Badge variant="outline">{ROLE_LABELS[m.role]}</Badge>
                  </CardTitle>
                  <CardDescription>{m.organization_slug}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
