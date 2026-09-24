import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AiVisibilityPage } from "@/features/ai-visibility/ai-page";

export const metadata: Metadata = { title: "AI visibility" };

export default async function AiVisibility({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <AiVisibilityPage projectId={projectId} />;
}
