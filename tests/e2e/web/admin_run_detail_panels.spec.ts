import path from "node:path";
import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("admin run detail panels and audit export", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-admin-detail-${Date.now()}`,
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
      requirements: { business_prompt: "Admin run detail panels" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await request.post(`/v1/runs/${runId}/maker/launch-eval`, { headers });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto(`/v1/admin/app/runs/${runId}`);

  await expect(page.getByTestId("admin-run-audit-export")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research briefs" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Stitch / transplant" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Integration adapter" })).toBeVisible();
  await expect(page.getByTestId("admin-factory-evidence-panel")).toBeVisible();
  await expect(page.getByTestId("admin-launch-scorecard-panel")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Findings", exact: true, level: 3 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Critic matrix" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Critic reliability" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Probation notices" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Policy compare" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Role execute (debug)" })).toBeVisible();
});
