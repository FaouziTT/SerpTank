import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SecuritySettings } from "@/features/security/security-settings";
import { StepUpProvider } from "@/features/security/step-up";
import { getSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Security" };

export default async function SecurityPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  return (
    <StepUpProvider>
      <SecuritySettings session={session} />
    </StepUpProvider>
  );
}
