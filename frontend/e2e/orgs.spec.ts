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

  // Technical audit: the e2e domain doesn't exist, so the crawl must fail honestly
  // (robots.txt unreachable) and the failure arrives over the SSE progress stream.
  const projectUrl = page.url();
  await page.getByRole("link", { name: "Open audit" }).click();
  await expect(page.getByRole("heading", { name: "Technical audit" })).toBeVisible();
  await expect(page.getByText("No audit yet")).toBeVisible();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(
    page.getByText(/The last audit failed: Your robots.txt could not be fetched/),
  ).toBeVisible({
    timeout: 30_000,
  });
  await page.goto(projectUrl);

  // Keywords: track, run a check with no live vendor configured (first-party only).
  await page.getByRole("link", { name: "Keywords" }).click();
  await expect(page.getByRole("heading", { name: "Keywords", exact: true })).toBeVisible();
  await page.getByLabel("Track keywords").fill("running shoes\nBuy Running Shoes");
  await page.getByRole("button", { name: "Add keywords" }).click();
  await expect(page.getByRole("cell", { name: "buy running shoes", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "transactional", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Check rankings now" }).click();
  await expect(page.getByRole("button", { name: "Check rankings now" })).toBeEnabled({
    timeout: 20_000,
  });
  await page.goto(projectUrl);

  // Search data: honest empty states, IndexNow key instructions, CSV import.
  await page.getByRole("link", { name: "Search data" }).click();
  await expect(page.getByRole("heading", { name: "Search data" })).toBeVisible();
  await expect(page.getByText("No data yet")).toBeVisible();
  await page.getByRole("button", { name: "Create IndexNow key" }).click();
  await expect(page.getByText("Key file not found yet")).toBeVisible();
  await page.getByLabel("CSV file").setInputFiles({
    name: "genai.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Date,Top pages,Impressions,Clicks\n2026-09-01,https://x/a,120,3\n2026-09-02,https://x/a,80,1\n",
    ),
  });
  await page.getByRole("button", { name: "Import CSV" }).click();
  await expect(page.getByText(/Imported 2 rows/)).toBeVisible();
  await expect(page.getByText("200", { exact: true })).toBeVisible(); // AI Overviews impressions
  await page
    .getByRole("navigation", { name: "Organization" })
    .getByRole("link", { name: "Integrations" })
    .click();
  await expect(
    page.getByText(/Google integrations aren.t configured on this server yet/),
  ).toBeVisible();
  await page.goto(projectUrl);

  // Content: honest empty states, and a brief built without any SERP vendor configured.
  await page.getByRole("link", { name: "Content" }).click();
  await expect(page.getByRole("heading", { name: "Content" })).toBeVisible();
  await expect(page.getByText("No analyses yet")).toBeVisible();
  await page.getByRole("tab", { name: "Content briefs" }).click();
  await page.getByLabel("Keyword to write for").fill("trail running shoes");
  await page.getByRole("button", { name: "Create brief" }).click();
  await expect(page.getByText(/No live SERP was available/)).toBeVisible();
  await page.getByRole("tab", { name: "Cannibalization" }).click();
  await expect(page.getByText("Search Console data needed")).toBeVisible();
  await page.goto(projectUrl);

  // AI visibility: with no answer engines configured, a run samples nothing and says so.
  await page.getByRole("link", { name: "AI visibility" }).click();
  await expect(page.getByRole("heading", { name: "AI visibility" })).toBeVisible();
  await expect(page.getByText("No AI answers sampled yet")).toBeVisible();
  await page.getByRole("tab", { name: "Prompts" }).click();
  await page.getByLabel("Prompts to track").fill("What are the best trail running shoes?");
  await page.getByRole("button", { name: "Add prompts" }).click();
  await expect(page.getByText("What are the best trail running shoes?")).toBeVisible();
  await page.getByRole("button", { name: "Check AI answers now" }).click();
  await expect(page.getByText("Done: 0 answers sampled.")).toBeVisible();
  await page.getByRole("tab", { name: "Readiness" }).click();
  await expect(page.getByText("Readiness needs a site audit")).toBeVisible();
  await page.goto(projectUrl);

  // Search Presence dashboard: honest blanks, an alert, and a CSV export via a signed link.
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Search Presence" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Notifications" })).toBeVisible();
  // Server-confirmed toggle: the box reflects the saved rule after the refetch.
  await page.getByLabel("Ranking drops on Google on").click();
  await expect(page.getByLabel("Ranking drops on Google on")).toBeChecked();
  await expect(page.getByLabel("Ranking drops on Google by email")).toBeEnabled();
  await page.getByRole("button", { name: "Export Rankings" }).click();
  await expect(page.getByRole("button", { name: "CSV" })).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "CSV" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^serptank-rankings-.*\.csv$/);
  await page.goto(projectUrl);

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
