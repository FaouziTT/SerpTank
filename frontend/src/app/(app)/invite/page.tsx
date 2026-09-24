import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AcceptInvite } from "@/features/orgs/accept-invite";
import { getSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Accept invitation", referrer: "no-referrer" };

export default async function InvitePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");
  const { token } = await searchParams;
  return (
    <AcceptInvite token={typeof token === "string" ? token : null} email={session.user.email} />
  );
}
