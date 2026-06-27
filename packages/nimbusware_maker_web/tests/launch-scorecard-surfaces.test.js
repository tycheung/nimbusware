import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const launchJs = readFileSync(resolve(import.meta.dirname, "../static/js/launch-scorecard.js"), "utf8");

describe("surface launch summary", () => {
  it("exports per-surface chip renderer", () => {
    expect(launchJs).toContain("renderSurfaceLaunchSummary");
    expect(launchJs).toContain("maker-surface-launch-summary");
    expect(launchJs).toContain("dev_env_http_regression_passed");
    expect(launchJs).toContain("dev_env_ui_regression_passed");
  });
});
