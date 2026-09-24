/**
 * Next.js 16 proxy (formerly "middleware").
 *
 * 1. Sets a strict, per-request nonce-based Content-Security-Policy.
 * 2. Redirects obviously unauthenticated visitors of app routes to /login.
 *    This is a UX shortcut only - the authoritative check is the server-side session
 *    lookup in `app/(app)/layout.tsx`, and the API enforces auth on every request.
 */
import { NextResponse, type NextRequest } from "next/server";

const APP_PREFIXES = ["/dashboard", "/settings", "/orgs", "/projects"];
const SESSION_COOKIES = ["__Host-st_session", "st_session"];

export function buildCsp(nonce: string, dev: boolean): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    // Radix positions popovers with inline style attributes.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${dev ? " ws:" : ""}`,
    "frame-src https://challenges.cloudflare.com",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self' https://accounts.google.com",
    "frame-ancestors 'none'",
    ...(dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

export function proxy(request: NextRequest): NextResponse {
  const { pathname, search } = request.nextUrl;
  const isAppRoute = APP_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  const hasSession = SESSION_COOKIES.some((name) => request.cookies.has(name));
  if (isAppRoute && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }

  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce, process.env.NODE_ENV !== "production");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("content-security-policy", csp);
  return response;
}

export const config = {
  // Skip the API (served by FastAPI), static assets and image optimisation.
  matcher: [
    {
      source: "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|ico|webp)$).*)",
      missing: [{ type: "header", key: "next-router-prefetch" }],
    },
  ],
};
