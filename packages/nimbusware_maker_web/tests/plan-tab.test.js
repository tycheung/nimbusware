import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const planJs = readFileSync(resolve(import.meta.dirname, "../static/js/tabs/plan.js"), "utf8");

describe("plan tab module", () => {
  it("loads backlog from campaigns API with refresh and badges", () => {
    expect(planJs).toContain("/campaigns/");
    expect(planJs).toContain("maker-plan-tree");
    expect(planJs).toContain("maker-plan-slice-badge");
    expect(planJs).toContain("maker-plan-surface-badge");
    expect(planJs).toContain("maker-plan-contract-gate");
    expect(planJs).toContain("slice.contract");
    expect(planJs).toContain("maker-progress/stream");
    expect(planJs).toContain("maker-progress?simple=true");
    expect(planJs).toContain("maker-plan-current-slice");
    expect(planJs).toContain("maker-plan-maintenance");
    expect(planJs).toContain("plan-slice--current");
    expect(planJs).toContain("unmountPlan");
  });
});
