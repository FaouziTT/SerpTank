import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { KeywordsPage } from "@/features/keywords/keywords-page";

export const metadata: Metadata = { title: "Keywords" };

export default async function Keywords({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <KeywordsPage projectId={projectId} />;
}
