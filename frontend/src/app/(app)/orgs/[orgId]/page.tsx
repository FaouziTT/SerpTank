import type { Metadata } from "next";

import { OrgOverview } from "@/features/orgs/org-overview";

export const metadata: Metadata = { title: "Projects" };

export default function OrgPage() {
  return <OrgOverview />;
}
