import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AuditPage } from "@/features/audit/audit-page";

export const metadata: Metadata = { title: "Technical audit" };

export default async function Audit({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <AuditPage projectId={projectId} />;
}
