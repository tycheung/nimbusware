import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("settings tab runs launch check for attached run", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-settings-launch-${Date.now()}`,
      workspace_path: fixtureWorkspace,
      template: "attach",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id as string;

  const runResp = await request.post("/v1/runs", {
    data: {
      workflow_profile: "micro_slice",
      project_id: projectId,
      requirements: { business_prompt: "Settings launch check replay" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/settings`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/settings");
  await expect(page.getByTestId("maker-settings-run-launch-eval")).toBeVisible();
  await expect(page.getByTestId("maker-settings-launch-run-hint")).toContainText(runId.slice(0, 8));
  await page.getByTestId("maker-settings-run-launch-eval").click();
  await expect(page.getByTestId("maker-settings-scorecard-aggregate")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-settings-scorecard-maturity")).toBeVisible();
  await expect(page.getByTestId("maker-settings-launch-scorecard")).toContainText("security");
});
