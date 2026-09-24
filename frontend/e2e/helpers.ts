import { expect, type Page } from "@playwright/test";

import { latestEmailTo, linkFrom } from "./mailpit";

export const PASSWORD = "correct horse battery staple 42";

export function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

export async function register(page: Page, email: string, fullName = "Erin Endtoend") {
  await page.goto("/register");
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  // Registration is rate limited per IP (a burst of 3, then one per 20s). Every e2e user
  // comes from 127.0.0.1, so wait out the limiter instead of weakening it for tests.
  for (let attempt = 0; attempt < 4; attempt++) {
    await page.getByRole("button", { name: "Create account" }).click();
    const done = page.getByRole("heading", { name: "Check your email" });
    const limited = page.getByText("Too many requests");
    await expect(done.or(limited)).toBeVisible();
    if (await done.isVisible()) return;
    await page.waitForTimeout(21_000);
  }
  throw new Error("Registration stayed rate limited");
}

export async function verify(page: Page, email: string) {
  const link = linkFrom(await latestEmailTo(email, "Verify your SerpTank email"));
  await page.goto(link.replace(/^https?:\/\/[^/]+/, ""));
  await expect(page.getByRole("heading", { name: "Email verified" })).toBeVisible();
}

export async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

/** Register, verify and sign in a fresh user; returns the email. */
export async function newSignedInUser(page: Page, fullName?: string): Promise<string> {
  const email = uniqueEmail();
  await register(page, email, fullName);
  await verify(page, email);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
  return email;
}
