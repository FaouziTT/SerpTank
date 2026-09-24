import type { Metadata } from "next";

import { OrgSettings } from "@/features/orgs/org-settings";

export const metadata: Metadata = { title: "Organization settings" };

export default function SettingsPage() {
  return <OrgSettings />;
}
