import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { setCsrfToken } from "@/lib/api/client";

import { StepUpProvider } from "./step-up";
import { YourDataCard } from "./your-data";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace, refresh: vi.fn() }),
}));

const server = setupServer(
  http.get("*/api/v1/auth/csrf", () => HttpResponse.json({ csrf_token: "t" })),
);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  setCsrfToken(null);
});
afterAll(() => server.close());

describe("YourDataCard", () => {
  it("explains the last-owner rule when deletion is refused", async () => {
    server.use(
      http.delete("*/api/v1/auth/me", () =>
        HttpResponse.json(
          {
            type: "x",
            title: "You are the last owner of an organization",
            status: 409,
            code: "last_owner",
            detail: "Transfer ownership or delete these organizations first: Acme.",
          },
          { status: 409 },
        ),
      ),
    );
    render(
      <StepUpProvider>
        <YourDataCard />
      </StepUpProvider>,
    );
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: "Delete my account" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Type DELETE to confirm"), "DELETE");
    await user.click(button);
    await user.click(await screen.findByRole("button", { name: "Delete account" }));
    expect(await screen.findByText(/delete these organizations first: Acme/)).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
