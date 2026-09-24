import type { Metadata } from "next";
import { Suspense } from "react";

import { IntegrationsPage } from "@/features/integrations/integrations-page";

export const metadata: Metadata = { title: "Integrations" };

export default function Integrations() {
  return (
    <Suspense>
      <IntegrationsPage />
    </Suspense>
  );
}
