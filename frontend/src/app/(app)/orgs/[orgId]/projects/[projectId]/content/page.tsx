import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ContentPage } from "@/features/content/content-page";

export const metadata: Metadata = { title: "Content" };

export default async function Content({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <ContentPage projectId={projectId} />;
}
