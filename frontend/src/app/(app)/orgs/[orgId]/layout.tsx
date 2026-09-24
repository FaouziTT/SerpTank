import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { StepUpProvider } from "@/features/security/step-up";
import type { Organization } from "@/features/orgs/api";
import { OrgProvider } from "@/features/orgs/org-context";
import { serverApiGet } from "@/lib/api/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Resolves the organization (and the caller's role) server-side. Foreign or unknown
 * organizations are a 404 - the API never confirms that someone else's org exists.
 */
export default async function OrgLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgId: string }>;
}) {
  const { orgId } = await params;
  if (!UUID.test(orgId)) notFound();
  const { status, data, code } = await serverApiGet<Organization>(`/api/v1/orgs/${orgId}`);
  if (status === 404 || status === 422) notFound();
  if (code === "mfa_required") {
    return (
      <Alert className="max-w-xl">
        <AlertTitle>Two-factor authentication required</AlertTitle>
        <AlertDescription>
          This organization requires two-factor authentication.{" "}
          <Link href="/settings/security" className="underline">
            Set it up in your security settings
          </Link>{" "}
          to continue.
        </AlertDescription>
      </Alert>
    );
  }
  if (!data) throw new Error("Could not load the organization.");
  return (
    <OrgProvider org={data}>
      <StepUpProvider>{children}</StepUpProvider>
    </OrgProvider>
  );
}
