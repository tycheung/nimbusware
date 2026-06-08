import path from "node:path";
import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("admin run detail factory evidence panel", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-admin-factory-${Date.now()}`,
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
      requirements: { business_prompt: "Admin factory evidence panel" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const evidenceResp = await request.get(`/v1/runs/${runId}/factory-evidence`, { headers });
  expect(evidenceResp.ok()).toBeTruthy();

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto(`/v1/admin/app/runs/${runId}`);
  await expect(page.getByTestId("admin-factory-evidence-panel")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("admin-factory-evidence-download")).toBeVisible();
});
