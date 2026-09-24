import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PresencePage } from "@/features/reports/presence-page";

export const metadata: Metadata = { title: "Search Presence" };

export default async function Presence({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <PresencePage projectId={projectId} />;
}
