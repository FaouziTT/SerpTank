import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProjectDetail } from "@/features/orgs/project-detail";

export const metadata: Metadata = { title: "Project" };

export default async function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <ProjectDetail projectId={projectId} />;
}
