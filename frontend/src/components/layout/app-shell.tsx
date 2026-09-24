"use client";

import { LayoutDashboard, LogOut, Shield } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { authApi, type SessionResponse } from "@/features/auth/api";
import { currentOrgId, OrgSwitcher, orgNavItems } from "@/features/orgs/org-nav";
import { NotificationBell } from "@/features/reports/notifications";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "All organizations", icon: LayoutDashboard },
  { href: "/settings/security", label: "Account security", icon: Shield },
];

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof Shield;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "hover:bg-muted flex items-center gap-2 rounded-md px-2 py-1.5 text-sm",
        active && "bg-muted font-medium",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden /> {label}
    </Link>
  );
}

export function AppShell({ session, children }: { session: SessionResponse; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const orgId = currentOrgId(pathname);
  const membership = session.memberships.find((m) => m.organization_id === orgId);

  async function signOut() {
    try {
      await authApi.logout();
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <div className="flex min-h-screen">
      <aside className="bg-muted/30 hidden w-60 shrink-0 border-r p-4 md:block">
        <Link href="/dashboard" className="mb-6 block px-2 text-lg font-semibold">
          SerpTank
        </Link>
        <div className="mb-4">
          <OrgSwitcher session={session} />
        </div>
        {membership ? (
          <nav aria-label="Organization" className="mb-6 space-y-1">
            {orgNavItems(membership.organization_id, membership.role).map((item) => (
              <NavLink key={item.href} {...item} active={item.isActive(pathname)} />
            ))}
          </nav>
        ) : null}
        <nav aria-label="Account" className="space-y-1">
          {NAV.map((item) => (
            <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} />
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4">
          <span className="text-muted-foreground text-sm md:hidden">SerpTank</span>
          <div className="ml-auto flex items-center gap-1">
            {membership && membership.role !== "billing" ? (
              <NotificationBell orgId={membership.organization_id} />
            ) : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" aria-label="Account menu">
                  {session.user.full_name || session.user.email}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel className="text-muted-foreground font-normal">
                  {session.user.email}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings/security">Security settings</Link>
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={signOut}>
                  <LogOut className="mr-2 h-4 w-4" aria-hidden /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
