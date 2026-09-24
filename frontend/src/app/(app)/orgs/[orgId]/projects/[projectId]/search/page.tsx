import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SearchDataPage } from "@/features/integrations/search-data-page";

export const metadata: Metadata = { title: "Search data" };

export default async function SearchData({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(projectId)) notFound();
  return <SearchDataPage projectId={projectId} />;
}
