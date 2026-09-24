import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { setCsrfToken } from "@/lib/api/client";

import { LoginForm } from "./login-form";

const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams("next=/settings/security"),
}));

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
  push.mockReset();
  replace.mockReset();
});
afterAll(() => server.close());

async function fillAndSubmit() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), "ana@example.com");
  await user.type(screen.getByLabelText("Password"), "a long enough passphrase");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginForm", () => {
  it("validates input before calling the API", async () => {
    render(<LoginForm googleEnabled={false} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("shows the API's generic error message", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json(
          {
            type: "x",
            title: "Sign-in failed",
            status: 401,
            code: "invalid_credentials",
            detail: "Incorrect email or password.",
          },
          { status: 401 },
        ),
      ),
    );
    render(<LoginForm googleEnabled={false} />);
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
  });

  it("redirects to the MFA step, preserving the safe next path", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json({ status: "mfa_required", csrf_token: "t2", mfa_methods: ["totp"] }),
      ),
    );
    render(<LoginForm googleEnabled={false} />);
    await fillAndSubmit();
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/login/mfa?next=%2Fsettings%2Fsecurity"),
    );
  });

  it("navigates to the next page after a successful login", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json({ status: "authenticated", csrf_token: "t2", user: null }),
      ),
    );
    render(<LoginForm googleEnabled={false} />);
    await fillAndSubmit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/settings/security"));
  });
});
