import { describe, expect, it } from "vitest";

import { safeNextPath } from "./api";

describe("safeNextPath (open-redirect protection)", () => {
  it.each([
    [null, "/dashboard"],
    ["/settings/security", "/settings/security"],
    ["/dashboard?x=1", "/dashboard?x=1"],
    ["https://evil.example", "/dashboard"],
    ["//evil.example", "/dashboard"],
    ["/\\evil.example", "/dashboard"],
    ["javascript:alert(1)", "/dashboard"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});
