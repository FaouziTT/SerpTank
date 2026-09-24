"use client";

import {
  Building2,
  Check,
  ChevronsUpDown,
  FolderKanban,
  History,
  Plug,
  Plus,
  Settings,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { SessionResponse } from "@/features/auth/api";
import { cn } from "@/lib/utils";

import type { MemberRole } from "./api";
import { can } from "./permissions";

/** The organization id in the current URL (`/orgs/<id>/...`), if any. */
export function currentOrgId(pathname: string): string | null {
  const match = /^\/orgs\/([0-9a-f-]{36})(?:\/|$)/i.exec(pathname);
  return match?.[1] ?? null;
}

export function OrgSwitcher({ session }: { session: SessionResponse }) {
  const pathname = usePathname();
  const orgId = currentOrgId(pathname);
  const current = session.memberships.find((m) => m.organization_id === orgId);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-between"
          aria-label="Switch organization"
        >
          <span className="flex min-w-0 items-center gap-2">
            <Building2 className="h-4 w-4 shrink-0" aria-hidden />
            <span className="truncate">{current?.organization_name ?? "Select organization"}</span>
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel className="text-muted-foreground font-normal">
          Organizations
        </DropdownMenuLabel>
        {session.memberships.map((m) => (
          <DropdownMenuItem key={m.organization_id} asChild>
            <Link href={`/orgs/${m.organization_id}`}>
              <Check
                className={cn(
                  "mr-2 h-4 w-4",
                  m.organization_id === orgId ? "opacity-100" : "opacity-0",
                )}
                aria-hidden
              />
              <span className="truncate">{m.organization_name}</span>
            </Link>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/orgs/new">
            <Plus className="mr-2 h-4 w-4" aria-hidden /> New organization
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Links for the organization in the URL, filtered by the caller's role. */
export function orgNavItems(orgId: string, role: MemberRole) {
  const base = `/orgs/${orgId}`;
  return [
    {
      href: base,
      label: "Projects",
      icon: FolderKanban,
      match: [base, `${base}/projects`],
      show: role !== "billing",
    },
    { href: `${base}/members`, label: "Members", icon: Users, show: role !== "billing" },
    { href: `${base}/integrations`, label: "Integrations", icon: Plug, show: role !== "billing" },
    { href: `${base}/audit`, label: "Audit log", icon: History, show: can(role, "audit:read") },
    { href: `${base}/settings`, label: "Settings", icon: Settings, show: true },
  ]
    .filter((item) => item.show)
    .map(({ match, ...item }) => ({
      ...item,
      isActive: (pathname: string) =>
        match
          ? pathname === match[0] || pathname.startsWith(`${match[1]}/`)
          : pathname === item.href || pathname.startsWith(`${item.href}/`),
    }));
}
