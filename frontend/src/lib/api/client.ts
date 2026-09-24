/**
 * Typed browser API client (generated types + openapi-fetch).
 *
 * Security:
 * - Same-origin requests only (`/api/v1/...`); cookies are HttpOnly and never touched here.
 * - Every unsafe request carries `X-CSRF-Token`. The token is fetched from
 *   `GET /api/v1/auth/csrf` (which also sets the pre-session cookie) and replaced whenever
 *   the API returns a new one (login, MFA, re-auth, password change rotate the session).
 * - Errors are normalised into `ApiError` (RFC 9457) - never raw exception text.
 */
import createClient, { type Middleware } from "openapi-fetch";

import { toApiError } from "./problem";
import type { paths } from "./schema";

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Same-origin base URL (explicit so it also works in test environments). */
function origin(): string {
  return typeof window === "undefined" ? "" : window.location.origin;
}

let csrfToken: string | null = null;
let csrfInFlight: Promise<string> | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export async function ensureCsrfToken(force = false): Promise<string> {
  if (csrfToken && !force) return csrfToken;
  csrfInFlight ??= fetch(`${origin()}/api/v1/auth/csrf`, { credentials: "same-origin" })
    .then(async (res) => {
      if (!res.ok) throw toApiError(res.status, await res.json().catch(() => null));
      const body = (await res.json()) as { csrf_token: string };
      csrfToken = body.csrf_token;
      return body.csrf_token;
    })
    .finally(() => {
      csrfInFlight = null;
    });
  return csrfInFlight;
}

export const csrfMiddleware: Middleware = {
  async onRequest({ request }) {
    if (UNSAFE.has(request.method.toUpperCase())) {
      request.headers.set("X-CSRF-Token", await ensureCsrfToken());
    }
    return request;
  },
  async onResponse({ response }) {
    const type = response.headers.get("content-type") ?? "";
    if (!response.ok || response.status === 204 || !type.includes("application/json")) {
      return response;
    }
    try {
      const body: unknown = await response.clone().json();
      if (body && typeof body === "object" && "csrf_token" in body) {
        const token = (body as { csrf_token: unknown }).csrf_token;
        if (typeof token === "string") setCsrfToken(token);
      }
    } catch {
      // Empty or non-JSON body: nothing to adopt.
    }
    return response;
  },
};

export const api = createClient<paths>({
  baseUrl: origin(),
  credentials: "same-origin",
  // Resolve fetch per call (not at import) so instrumentation/test doubles apply.
  fetch: (request) => globalThis.fetch(request),
});
api.use(csrfMiddleware);

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Unwrap an openapi-fetch result: return data or throw `ApiError`. */
export async function unwrap<T>(promise: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (!response.ok) throw toApiError(response.status, error);
  return data as T;
}
