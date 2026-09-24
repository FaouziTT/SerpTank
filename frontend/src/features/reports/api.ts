/** Typed wrappers for Search Presence, exports, alerts and notifications. */
import { api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type S = components["schemas"];
export type Presence = S["PresenceOut"];
export type ExportRow = S["ExportOut"];
export type ExportKind = S["ExportRequest"]["kind"];
export type AlertRule = S["AlertRuleOut"];
export type NotificationList = S["NotificationList"];
export type AppNotification = S["NotificationOut"];
export type AlertKind =
  | "rank_drop"
  | "ai_citation_lost"
  | "audit_regression"
  | "cwv_poor"
  | "indexing_lost"
  | "weekly_digest";

/** Shapes inside `Presence` (mirrors backend `reports/presence.py`). */
export interface EnginePresence {
  engine: string;
  keywords: number;
  share_of_voice: number | null;
  distribution: Record<string, number>;
  weight: number;
}
export interface GscTotals {
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
}

const p = (org_id: string, project_id: string) => ({ params: { path: { org_id, project_id } } });

export const reportKeys = {
  project: (orgId: string, projectId: string) => ["orgs", orgId, "projects", projectId, "reports"],
  notifications: (orgId: string) => ["orgs", orgId, "notifications"],
};

export const reportsApi = {
  presence: (orgId: string, projectId: string, marketId: string) =>
    unwrap(
      api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/presence", {
        params: { path: { org_id: orgId, project_id: projectId }, query: { market_id: marketId } },
      }),
    ),
  exports: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/exports", p(orgId, projectId))),
  startExport: (orgId: string, projectId: string, kind: ExportKind) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/exports", {
        ...p(orgId, projectId),
        body: { kind },
      }),
    ),
  exportLink: (orgId: string, projectId: string, exportId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/projects/{project_id}/exports/{export_id}/link", {
        params: { path: { org_id: orgId, project_id: projectId, export_id: exportId } },
      }),
    ),
  alerts: (orgId: string, projectId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/projects/{project_id}/alerts", p(orgId, projectId))),
  setAlert: (
    orgId: string,
    projectId: string,
    kind: AlertKind,
    body: { active: boolean; threshold: number | null; email: boolean },
  ) =>
    unwrap(
      api.PUT("/api/v1/orgs/{org_id}/projects/{project_id}/alerts/{kind}", {
        params: { path: { org_id: orgId, project_id: projectId, kind } },
        body,
      }),
    ),
  notifications: (orgId: string) =>
    unwrap(api.GET("/api/v1/orgs/{org_id}/notifications", { params: { path: { org_id: orgId } } })),
  markRead: (orgId: string, id: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/notifications/{notification_id}/read", {
        params: { path: { org_id: orgId, notification_id: id } },
      }),
    ),
  markAllRead: (orgId: string) =>
    unwrap(
      api.POST("/api/v1/orgs/{org_id}/notifications/read-all", {
        params: { path: { org_id: orgId } },
      }),
    ),
};
