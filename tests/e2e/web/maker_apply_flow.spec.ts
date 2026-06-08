import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("review tab apply-slice click after API setup", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-apply-${Date.now()}`,
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
      requirements: { business_prompt: "Playwright apply flow" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const approve = await request.post(`/v1/runs/${runId}/maker/plan/approve`);
  expect(approve.ok()).toBeTruthy();
  const prepare = await request.post(`/v1/runs/${runId}/maker/slices/prepare`);
  expect(prepare.ok()).toBeTruthy();
  const prepBody = await prepare.json();
  expect(prepBody.status).toBe("awaiting_approval");

  const pendingCheck = await request.get(`/v1/runs/${runId}/maker/pending`);
  expect(pendingCheck.ok()).toBeTruthy();
  const pendingBody = await pendingCheck.json();
  expect(pendingBody.awaiting_approval).toBe(true);
  expect(pendingBody.pending).toBeTruthy();

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");
  await expect(page.getByTestId("maker-review-refresh")).toBeVisible();

  const pendingResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/runs/${runId}/maker/pending`) && resp.ok(),
  );
  await page.getByTestId("maker-review-refresh").click();
  await pendingResponse;
  await expect(page.getByTestId("maker-review-slice-status")).toContainText("awaiting your approval");
  await expect(page.getByTestId("maker-review-pending-card")).toBeVisible();
  await expect(page.getByTestId("maker-review-apply-slice")).toBeVisible();

  const applyResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/runs/${runId}/maker/slices/apply`) && resp.ok(),
  );
  await page.getByTestId("maker-review-apply-slice").click();
  await applyResponse;
  await expect(page.getByTestId("maker-review-slice-status")).toContainText("no pending approval");
  await expect(page.getByTestId("maker-review-last-snapshot")).toBeVisible();
});
