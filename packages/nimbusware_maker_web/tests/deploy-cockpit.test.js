import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { deployStateFromTimeline } from "../static/js/deploy_cockpit.js";

const deployJs = readFileSync(resolve(import.meta.dirname, "../static/js/deploy_cockpit.js"), "utf8");
const settingsDeployJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/settings_deploy_ui.js"),
  "utf8",
);

describe("deploy cockpit module", () => {
  it("exports timeline parser and cockpit test ids", () => {
    expect(deployJs).toContain("data-deploy-scope");
    expect(deployJs).toContain("maker-deploy-approve-");
    expect(deployJs).toContain("maker-deploy-apply-");
    expect(deployJs).toContain("maker-deploy-smoke-");
    expect(deployJs).toContain("maker-deploy-rollback-");
    expect(deployJs).toContain("maker-deploy-environment-");
    expect(deployJs).toContain("/platform/deploy/environments");
    expect(deployJs).toContain("deploy.approved");
    expect(deployJs).toContain("/platform/deploy/apply");
    expect(deployJs).toContain("/platform/deploy/smoke");
    expect(deployJs).toContain("/platform/deploy/rollback");
  });

  it("detects CI pass and plan artifact from timeline", () => {
    const state = deployStateFromTimeline([
      {
        event_type: "stage.passed",
        payload: { stage_name: "ci.plan" },
        metadata: { detail: "terraform plan ok", plan_artifact: "plan.tfplan" },
      },
    ]);
    expect(state.ciStatus).toBe("passed");
    expect(state.planArtifact).toBe("plan.tfplan");
  });

  it("settings deploy section stores local labels", () => {
    expect(settingsDeployJs).toContain("maker-settings-deploy");
    expect(settingsDeployJs).toContain("maker-settings-deploy-environment");
  });
});
