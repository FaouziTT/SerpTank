/**
 * Mirror of the backend role matrix (`tenancy/policies.py`), used only to hide controls
 * a member can't use. The API remains the authority: it re-checks every request.
 */
import type { MemberRole } from "./api";

export type Permission =
  | "org:update"
  | "org:delete"
  | "members:manage"
  | "project:write"
  | "api_keys:manage"
  | "audit:read"
  | "integrations:manage"
  | "billing:manage";

const ADMIN: ReadonlySet<Permission> = new Set([
  "org:update",
  "members:manage",
  "project:write",
  "api_keys:manage",
  "audit:read",
  "integrations:manage",
  "billing:manage",
]);

const MATRIX: Record<MemberRole, ReadonlySet<Permission>> = {
  owner: new Set([...ADMIN, "org:delete"]),
  admin: ADMIN,
  editor: new Set(["project:write"]),
  viewer: new Set(),
  billing: new Set(["billing:manage"]),
};

export function can(role: MemberRole | undefined, permission: Permission): boolean {
  return role !== undefined && MATRIX[role].has(permission);
}

/** Roles an actor may grant (only owners manage ownership). */
export function assignableRoles(actor: MemberRole): MemberRole[] {
  if (actor === "owner") return ["owner", "admin", "editor", "viewer", "billing"];
  if (actor === "admin") return ["admin", "editor", "viewer", "billing"];
  return [];
}

export const ROLE_LABELS: Record<MemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  editor: "Editor",
  viewer: "Viewer",
  billing: "Billing",
};
