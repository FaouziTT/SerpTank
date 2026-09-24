import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import { api, ensureCsrfToken, setCsrfToken, unwrap } from "./client";
import { ApiError, toApiError } from "./problem";

const seen: Request[] = [];
const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "token-1" })),
  http.post("*/api/v1/auth/logout", ({ request }) => {
    seen.push(request);
    return new HttpResponse(null, { status: 204 });
  }),
  http.post("*/api/v1/auth/reauth", () => HttpResponse.json({ csrf_token: "rotated-token" })),
  http.get("*/api/v1/auth/session", ({ request }) => {
    seen.push(request);
    return HttpResponse.json(
      {
        type: "x",
        title: "Authentication required",
        status: 401,
        code: "authentication_required",
        detail: "Please sign in.",
      },
      { status: 401, headers: { "content-type": "application/problem+json" } },
    );
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  seen.length = 0;
  setCsrfToken(null);
  server.resetHandlers();
});
afterAll(() => server.close());

describe("api client", () => {
  it("adds the CSRF token to unsafe requests only", async () => {
    await unwrap(api.POST("/api/v1/auth/logout"));
    expect(seen[0]?.headers.get("x-csrf-token")).toBe("token-1");
    await expect(unwrap(api.GET("/api/v1/auth/session"))).rejects.toBeInstanceOf(ApiError);
    expect(seen[1]?.headers.get("x-csrf-token")).toBeNull();
  });

  it("adopts rotated CSRF tokens from responses", async () => {
    await unwrap(api.POST("/api/v1/auth/reauth", { body: { password: "x" } }));
    expect(await ensureCsrfToken()).toBe("rotated-token");
  });

  it("turns problem details into ApiError with a stable code", async () => {
    const error = await unwrap(api.GET("/api/v1/auth/session")).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("authentication_required");
    expect((error as ApiError).userMessage).toBe("Please sign in.");
  });
});

describe("toApiError", () => {
  it("never exposes non-problem bodies", () => {
    const err = toApiError(500, "<html>stack trace secret</html>");
    expect(err.userMessage).toBe("Something went wrong");
    expect(err.code).toBe("internal_error");
  });

  it("maps validation errors to fields", () => {
    const err = toApiError(422, {
      type: "t",
      title: "Request validation failed",
      status: 422,
      code: "validation_failed",
      errors: [{ field: "email", message: "invalid", type: "value_error" }],
    });
    expect(err.fieldErrors()).toEqual({ email: "invalid" });
  });
});

describe("empty responses", () => {
  it("handles 204 No Content with a JSON content-type", async () => {
    server.use(
      http.post(
        "*/api/v1/auth/verify-email",
        () =>
          new HttpResponse(null, { status: 204, headers: { "content-type": "application/json" } }),
      ),
    );
    await expect(
      unwrap(api.POST("/api/v1/auth/verify-email", { body: { token: "t".repeat(20) } })),
    ).resolves.toBeUndefined();
  });
});
