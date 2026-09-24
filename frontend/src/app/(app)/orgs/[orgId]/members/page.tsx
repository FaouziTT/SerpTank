import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { MembersPage } from "@/features/orgs/members";
import { getSession } from "@/lib/api/server";

export const metadata: Metadata = { title: "Members" };

export default async function Members() {
  const session = await getSession();
  if (!session) redirect("/login");
  return <MembersPage currentUserId={session.user.id} />;
}
