import { expect, test, type Page } from "@playwright/test";

import { latestEmailTo, linkFrom } from "./mailpit";

const PASSWORD = "correct horse battery staple 42";

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

async function register(page: Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Erin Endtoend");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
}

async function verify(page: Page, email: string) {
  const link = linkFrom(await latestEmailTo(email, "Verify your SerpTank email"));
  await page.goto(link.replace(/^https?:\/\/[^/]+/, ""));
  await expect(page.getByRole("heading", { name: "Email verified" })).toBeVisible();
}

async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test("register, verify, sign in, and see the dashboard", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  const email = uniqueEmail();
  await register(page, email);
  await verify(page, email);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: /Welcome, Erin/ })).toBeVisible();
  await expect(page.getByText("No organization yet")).toBeVisible();
  expect(errors).toEqual([]);
});

test("app routes redirect anonymous visitors and pages send a strict CSP", async ({ page }) => {
  const response = await page.goto("/settings/security");
  await expect(page).toHaveURL(/\/login\?next=%2Fsettings%2Fsecurity$/);
  const csp = response?.headers()["content-security-policy"] ?? "";
  expect(csp).toContain("'strict-dynamic'");
  expect(csp).toContain("frame-ancestors 'none'");
});

test("wrong password shows a generic error", async ({ page }) => {
  await signIn(page, "nobody-at-all@example.com");
  await expect(page.getByText("Incorrect email or password.")).toBeVisible();
});

test("enable TOTP with step-up, then sign in with a code", async ({ page, browser }) => {
  const email = uniqueEmail();
  await register(page, email);
  await verify(page, email);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.goto("/settings/security");
  await page.getByRole("button", { name: "Set up authenticator" }).click();
  // Step-up dialog: confirm identity with the password.
  await page.getByLabel("Password or authentication code").fill(PASSWORD);
  await page.getByRole("button", { name: "Confirm" }).click();
  const secret = (await page.locator("code").first().textContent())?.trim() ?? "";
  expect(secret).toMatch(/^[A-Z2-7]{32}$/);
  const { TOTP } = await import("./totp");
  await page.getByLabel("Code from your app").fill(TOTP(secret));
  await page.getByRole("button", { name: "Turn on" }).click();
  await expect(page.getByRole("list", { name: "Recovery codes" })).toBeVisible();

  const second = await browser.newPage();
  await signIn(second, email);
  await expect(second).toHaveURL(/\/login\/mfa/);
  await second.getByRole("button", { name: "Use a recovery code instead" }).click();
  const code =
    (await page
      .getByRole("list", { name: "Recovery codes" })
      .locator("li")
      .first()
      .textContent()) ?? "";
  await second.getByLabel("Recovery code").fill(code);
  await second.getByRole("button", { name: "Verify" }).click();
  await expect(second).toHaveURL(/\/dashboard$/);
});
