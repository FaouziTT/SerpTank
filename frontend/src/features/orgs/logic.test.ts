import { describe, expect, it } from "vitest";

import { DEFAULT_MARKET, marketErrors } from "./market-fields";
import { currentOrgId, orgNavItems } from "./org-nav";
import { assignableRoles, can } from "./permissions";

const ORG = "0192f1a4-1b2c-7d3e-8f40-123456789abc";

describe("permissions mirror", () => {
  it("matches the backend role matrix", () => {
    expect(can("owner", "org:delete")).toBe(true);
    expect(can("admin", "org:delete")).toBe(false);
    expect(can("admin", "members:manage")).toBe(true);
    expect(can("editor", "project:write")).toBe(true);
    expect(can("editor", "members:manage")).toBe(false);
    expect(can("viewer", "project:write")).toBe(false);
    expect(can("billing", "project:write")).toBe(false);
    expect(can(undefined, "project:write")).toBe(false);
  });

  it("only lets owners grant ownership", () => {
    expect(assignableRoles("owner")).toContain("owner");
    expect(assignableRoles("admin")).not.toContain("owner");
    expect(assignableRoles("editor")).toEqual([]);
  });
});

describe("marketErrors", () => {
  it("accepts the default market", () => {
    expect(marketErrors(DEFAULT_MARKET)).toEqual({});
  });

  it("rejects bad codes and empty engine lists", () => {
    const errors = marketErrors({
      ...DEFAULT_MARKET,
      country: "USA",
      language: "EN",
      search_engines: [],
    });
    expect(Object.keys(errors).sort()).toEqual(["country", "language", "search_engines"]);
  });

  it("accepts regional language tags", () => {
    expect(marketErrors({ ...DEFAULT_MARKET, language: "pt-BR" })).toEqual({});
  });
});

describe("org navigation", () => {
  it("extracts the org id from the path", () => {
    expect(currentOrgId(`/orgs/${ORG}/members`)).toBe(ORG);
    expect(currentOrgId(`/orgs/${ORG}`)).toBe(ORG);
    expect(currentOrgId("/orgs/new")).toBeNull();
    expect(currentOrgId("/dashboard")).toBeNull();
  });

  it("hides links the role cannot use", () => {
    const labels = (role: Parameters<typeof orgNavItems>[1]) =>
      orgNavItems(ORG, role).map((i) => i.label);
    expect(labels("owner")).toEqual([
      "Projects",
      "Members",
      "Integrations",
      "Audit log",
      "Billing",
      "Settings",
    ]);
    expect(labels("viewer")).toEqual(["Projects", "Members", "Integrations", "Settings"]);
    expect(labels("billing")).toEqual(["Billing", "Settings"]);
  });

  it("marks Projects active on project pages", () => {
    const projects = orgNavItems(ORG, "owner")[0]!;
    expect(projects.isActive(`/orgs/${ORG}`)).toBe(true);
    expect(projects.isActive(`/orgs/${ORG}/projects/abc`)).toBe(true);
    expect(projects.isActive(`/orgs/${ORG}/members`)).toBe(false);
  });
});
