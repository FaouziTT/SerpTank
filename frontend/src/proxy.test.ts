import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { buildCsp, proxy } from "./proxy";

describe("buildCsp", () => {
  it("is strict in production", () => {
    const csp = buildCsp("abc", false);
    expect(csp).toContain("script-src 'self' 'nonce-abc' 'strict-dynamic'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'none'");
    expect(csp).not.toContain("unsafe-eval");
  });
});

describe("proxy", () => {
  it("redirects app routes without a session cookie to login", () => {
    const res = proxy(new NextRequest("http://localhost/settings/security?tab=1"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost/login?next=%2Fsettings%2Fsecurity%3Ftab%3D1",
    );
  });

  it("sets a fresh nonce-based CSP for other pages", () => {
    const a = proxy(new NextRequest("http://localhost/login"));
    const b = proxy(new NextRequest("http://localhost/login"));
    const nonceA = /nonce-([^']+)/.exec(a.headers.get("content-security-policy") ?? "")?.[1];
    const nonceB = /nonce-([^']+)/.exec(b.headers.get("content-security-policy") ?? "")?.[1];
    expect(nonceA).toBeTruthy();
    expect(nonceA).not.toBe(nonceB);
  });

  it("lets requests with a session cookie through (server layout re-validates)", () => {
    const req = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: "st_session=abc" },
    });
    expect(proxy(req).status).toBe(200);
  });
});
