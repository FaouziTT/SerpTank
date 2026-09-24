import type { Metadata } from "next";

import { CreateOrgForm } from "@/features/orgs/create-org-form";

export const metadata: Metadata = { title: "New organization" };

export default function NewOrgPage() {
  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New organization</h1>
        <p className="text-muted-foreground text-sm">
          Organizations hold your projects, members and billing. You can invite your team next.
        </p>
      </div>
      <CreateOrgForm />
    </div>
  );
}
