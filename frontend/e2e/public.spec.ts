import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { PASSWORD, register, signIn, uniqueEmail, verify } from "./helpers";

test("public site: honest pages, crawl directives, no accessibility violations", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rank on Google. Get cited by AI." }),
  ).toBeVisible();
  const robotsMeta = await page.locator('meta[name="robots"]').getAttribute("content");
  expect(robotsMeta).toContain("index");
  expect(robotsMeta).not.toContain("noindex");
  for (const path of ["/", "/pricing", "/privacy"]) {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(
      results.violations.map((v) => v.id),
      path,
    ).toEqual([]);
  }

  await page.goto("/pricing");
  for (const plan of ["Free", "Pro", "Agency"]) {
    await expect(page.getByRole("region", { name: plan })).toBeVisible();
  }
  await page.goto("/privacy");
  await expect(page.getByRole("note")).toContainText("hasn't published its operator details");
  await page.goto("/subprocessors");
  await expect(page.getByRole("heading", { name: "Subprocessors" })).toBeVisible();

  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Disallow: /orgs");
  expect(robots).toContain("Sitemap:");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("/pricing");
  // No security contact configured in e2e: no security.txt rather than a made-up one.
  expect((await request.get("/.well-known/security.txt")).status()).toBe(404);
});

test("export my data, then delete my account", async ({ page }) => {
  const email = uniqueEmail();
  await register(page, email);
  await verify(page, email);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto("/settings/security");

  // Export needs a recent step-up: confirm the password when asked.
  await page.getByRole("button", { name: "Download my data" }).click();
  const secret = page.getByLabel("Password or authentication code");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    (async () => {
      await secret.waitFor({ timeout: 10_000 });
      await secret.fill(PASSWORD);
      await page.getByRole("button", { name: "Confirm" }).click();
    })(),
  ]);
  expect(download.suggestedFilename()).toBe("serptank-my-data.json");

  await page.getByLabel("Type DELETE to confirm").fill("DELETE");
  await page.getByRole("button", { name: "Delete my account" }).click();
  await page.getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Incorrect email or password.")).toBeVisible();
});
