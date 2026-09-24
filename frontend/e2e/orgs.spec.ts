import { expect, test } from "@playwright/test";

import { newSignedInUser } from "./helpers";
import { latestEmailTo, linkFrom } from "./mailpit";

test("create an org and project, verify instructions, invite an editor", async ({
  page,
  browser,
}) => {
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  await newSignedInUser(page, "Olive Owner");

  // Organization.
  await page.getByRole("link", { name: "Create organization" }).click();
  await page.getByLabel("Organization name").fill("E2E Agency");
  await page.getByRole("button", { name: "Create organization" }).click();
  await expect(page).toHaveURL(/\/orgs\/[0-9a-f-]{36}$/);
  const orgUrl = new URL(page.url()).pathname;
  await expect(page.getByText("No projects yet")).toBeVisible();

  // Project with the default Google market.
  await page.getByRole("button", { name: "Add a website" }).click();
  await page.getByLabel("Project name").fill("Main site");
  await page.getByLabel("Domain").fill("https://www.e2e-serptank-example.com/");
  await expect(page.getByRole("checkbox", { name: /Bing/ })).toBeDisabled();
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Main site" })).toBeVisible();
  await expect(page.getByText("www.e2e-serptank-example.com").first()).toBeVisible();

  // Domain verification instructions (the check itself needs real DNS).
  await page.getByRole("button", { name: "Use a DNS TXT record" }).click();
  await expect(page.getByText(/serptank-site-verification=/)).toBeVisible();

  // Invite a teammate as editor.
  await page.getByRole("link", { name: "Members" }).click();
  const invitee = `e2e-inv-${Date.now()}@example.com`;
  await page.getByLabel("Email", { exact: true }).fill(invitee);
  await page.getByLabel("Role", { exact: true }).selectOption("editor");
  await page.getByRole("button", { name: "Send invite" }).click();
  await expect(page.getByText(`Invitation sent to ${invitee}.`)).toBeVisible();
  await expect(page.getByRole("list", { name: "Pending invitations" })).toContainText(invitee);

  // The invitee signs up with the invited address and accepts.
  const context = await browser.newContext();
  const second = await context.newPage();
  const { register, verify, signIn } = await import("./helpers");
  await register(second, invitee, "Eddie Editor");
  await verify(second, invitee);
  await signIn(second, invitee);
  await expect(second).toHaveURL(/\/dashboard$/);
  const inviteLink = linkFrom(await latestEmailTo(invitee, "invited to join E2E Agency"));
  await second.goto(inviteLink.replace(/^https?:\/\/[^/]+/, ""));
  await expect(second).toHaveURL(/\/invite$/); // token removed from the address bar
  await second.getByRole("button", { name: "Accept invitation" }).click();
  await expect(second).toHaveURL(new RegExp(`${orgUrl}$`));
  await expect(second.getByText("Main site")).toBeVisible();
  // Editors don't get the audit log.
  await expect(second.getByRole("link", { name: "Audit log" })).toHaveCount(0);
  await context.close();

  // The owner sees the new member and the audit trail.
  await page.reload();
  await expect(page.getByText("Eddie Editor")).toBeVisible();
  await page.getByRole("link", { name: "Audit log" }).click();
  await expect(page.getByText("Invitation accepted")).toBeVisible();
  await expect(page.getByText("Project created")).toBeVisible();

  // Unknown or foreign organizations are a 404, never a 403.
  const response = await page.goto("/orgs/0192f1a4-1b2c-7d3e-8f40-123456789abc");
  expect(response?.status()).toBe(404);
  expect(errors.filter((e) => !/\b(404|429)\b/.test(e))).toEqual([]);
});
