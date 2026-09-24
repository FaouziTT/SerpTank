"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { Organization } from "./api";
import { can, type Permission } from "./permissions";

const OrgContext = createContext<Organization | null>(null);

/** Provides the current organization (resolved server-side, incl. the caller's role). */
export function OrgProvider({ org, children }: { org: Organization; children: ReactNode }) {
  return <OrgContext.Provider value={org}>{children}</OrgContext.Provider>;
}

export function useOrg(): Organization {
  const org = useContext(OrgContext);
  if (!org) throw new Error("useOrg must be used inside <OrgProvider>");
  return org;
}

export function useCan(permission: Permission): boolean {
  return can(useOrg().role, permission);
}
