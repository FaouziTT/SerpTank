/**
 * Typed wrappers around the organization, member, invitation and project APIs.
 * All functions throw `ApiError` (RFC 9457) on failure.
 */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type Organization = S["OrganizationWithRole"];
export type Member = S["MemberOut"];
export type MemberRole = S["MemberRole"];
export type Invitation = S["InvitationOut"];
export type Project = S["ProjectOut"];
export type Market = S["MarketOut"];
export type MarketIn = S["MarketIn"];
export type SearchEngine = S["SearchEngine"];
export type AIEngine = S["AIEngine"];
export type Entitlements = S["EntitlementsOut"];
export type ApiKey = S["ApiKeyOut"];
export type AuditEvent = S["AuditEventOut"];
export type VerificationMethod = S["VerificationMethod"];

const org = (org_id: string) => ({ params: { path: { org_id } } });
const project = (org_id: string, project_id: string) => ({
  params: { path: { org_id, project_id } },
});

export const orgsApi = {
  list: () => unwrap(api.GET("/api/v1/orgs")),
  get: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}", org(orgId))),
  create: (name: string) => unwrap(api.POST("/api/v1/orgs", { body: { name } })),
  update: (orgId: string, body: S["OrganizationUpdate"]) =>
    unwrap(api.PATCH("/api/v1/orgs/{org_id}", { ...org(orgId), body })),
  remove: (orgId: string) => unwrap(api.DELETE("/api/v1/orgs/{org_id}", org(orgId))),
  entitlements: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/entitlements", org(orgId))),

  members: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/members", org(orgId))),
  changeRole: (orgId: string, membershipId: string, role: MemberRole) =>
    unwrap(
      api.PATCH("/api/v1/orgs/{org_id}/members/{membership_id}", {
        params: { path: { org_id: orgId, membership_id: membershipId } },
        body: { role },
      }),
    ),
  removeMember: (orgId: string, membershipId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/members/{membership_id}", {
        params: { path: { org_id: orgId, membership_id: membershipId } },
      }),
    ),

  invitations: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/invitations", org(orgId))),
  invite: (orgId: string, email: string, role: MemberRole) =>
    unwrap(api.POST("/api/v1/orgs/{org_id}/invitations", { ...org(orgId), body: { email, role } })),
  revokeInvitation: (orgId: string, invitationId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/invitations/{invitation_id}", {
        params: { path: { org_id: orgId, invitation_id: invitationId } },
      }),
    ),
  acceptInvitation: (token: string) =>
    unwrap(api.POST("/api/v1/invitations/accept", { body: { token } })),

  apiKeys: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/api-keys", org(orgId))),
  createApiKey: (orgId: string, body: S["ApiKeyCreateRequest"]) =>
    unwrap(api.POST("/api/v1/orgs/{org_id}/api-keys", { ...org(orgId), body })),
  revokeApiKey: (orgId: string, keyId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/api-keys/{key_id}", {
        params: { path: { org_id: orgId, key_id: keyId } },
      }),
    ),
  auditEvents: (orgId: string, before?: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/audit-events", {
        params: { path: { org_id: orgId }, query: { limit: 50, before: before ?? null } },
      }),
    ),
};

export const projectsApi = {
  list: (orgId: string) => unwrap(api.GET("/api/v1/orgs/{org_id}/projects", org(orgId))),
  get: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}", project(orgId, projectId))),
  create: (orgId: string, body: S["ProjectCreate"]) =>
    unwrap(api.POST("/api/v1/orgs/{org_id}/projects", { ...org(orgId), body })),
  rename: (orgId: string, projectId: string, name: string) =>
    unwrap(
      api.PATCH("/api/v1/orgs/{org_id}/projects/{project_id}", {
        ...project(orgId, projectId),
        body: { name },
      }),
    ),
  remove: (orgId: string, projectId: string) =>
    unwrap(api.DELETE("/api/v1/orgs/{org_id}/projects/{project_id}", project(orgId, projectId))),
  addMarket: (orgId: string, projectId: string, body: MarketIn) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/markets", {
        ...project(orgId, projectId),
        body,
      }),
    ),
  removeMarket: (orgId: string, projectId: string, marketId: string) =>
    unwrap(
      api.DELETE("/api/v1/orgs/{org_id}/projects/{project_id}/markets/{market_id}", {
        params: { path: { org_id: orgId, project_id: projectId, market_id: marketId } },
      }),
    ),
  startVerification: (orgId: string, projectId: string, method: VerificationMethod) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/verification", {
        ...project(orgId, projectId),
        body: { method },
      }),
    ),
  checkVerification: (orgId: string, projectId: string) =>
    unwrap(
      api.POST(
        "/api/v1/orgs/{org_id}/projects/{project_id}/verification/check",
        project(orgId, projectId),
      ),
    ),
};

/** TanStack Query keys (one place so invalidation stays consistent). */
export const keys = {
  orgs: ["orgs"] as const,
  org: (id: string) => ["orgs", id] as const,
  entitlements: (id: string) => ["orgs", id, "entitlements"] as const,
  members: (id: string) => ["orgs", id, "members"] as const,
  invitations: (id: string) => ["orgs", id, "invitations"] as const,
  apiKeys: (id: string) => ["orgs", id, "api-keys"] as const,
  audit: (id: string) => ["orgs", id, "audit"] as const,
  projects: (id: string) => ["orgs", id, "projects"] as const,
  project: (id: string, projectId: string) => ["orgs", id, "projects", projectId] as const,
};
