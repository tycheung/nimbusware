import path from "node:path";
import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("admin run detail launch scorecard panel", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-admin-launch-${Date.now()}`,
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
      requirements: { business_prompt: "Admin launch scorecard replay" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const launchEval = await request.post(`/v1/runs/${runId}/maker/launch-eval`, { headers });
  expect(launchEval.ok()).toBeTruthy();

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto(`/v1/admin/app/runs/${runId}`);
  await expect(page.getByRole("heading", { name: "Launch eval" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("admin-launch-scorecard-panel")).toBeVisible();
  await expect(page.getByTestId("admin-launch-scorecard-panel")).toContainText("aggregate");
});
