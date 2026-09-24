/**
 * Server-side API access for React Server Components (authoritative auth checks).
 * Forwards the browser's cookies to the backend over the internal network.
 */
import "server-only";

import { cookies } from "next/headers";

import type { components } from "./schema";

export type SessionResponse = components["schemas"]["SessionResponse"];

const INTERNAL_API = process.env.SERPTANK_INTERNAL_API_URL ?? "http://127.0.0.1:8000";

export async function serverApiGet<T>(
  path: string,
): Promise<{ status: number; data: T | null; code: string | null }> {
  const cookieHeader = (await cookies())
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  const res = await fetch(`${INTERNAL_API}${path}`, {
    headers: { cookie: cookieHeader, accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    // Only the stable problem `code` is surfaced; never the raw body.
    const problem = (await res.json().catch(() => null)) as { code?: unknown } | null;
    const code = typeof problem?.code === "string" ? problem.code : null;
    return { status: res.status, data: null, code };
  }
  return { status: res.status, data: (await res.json()) as T, code: null };
}

/** The signed-in user's session, or null when not (fully) authenticated. */
export async function getSession(): Promise<SessionResponse | null> {
  const { data } = await serverApiGet<SessionResponse>("/api/v1/auth/session");
  return data;
}
