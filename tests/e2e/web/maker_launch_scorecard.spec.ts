import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("review tab loads launch scorecard after API run", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-launch-${Date.now()}`,
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
      requirements: { business_prompt: "Launch scorecard UI replay" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const launchEval = await request.post(`/v1/runs/${runId}/maker/launch-eval`);
  expect(launchEval.ok()).toBeTruthy();
  const scorecard = await launchEval.json();
  expect(scorecard.aggregate).toBeGreaterThan(0);

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");
  await expect(page.getByTestId("maker-review-launch-scorecard")).toBeVisible();

  const timelineResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/runs/${runId}/timeline`) && resp.ok(),
  );
  await page.getByTestId("maker-review-launch-scorecard").click();
  await timelineResponse;
  await expect(page.getByTestId("maker-review-scorecard-body")).toContainText("aggregate");
  await expect(page.getByTestId("maker-review-scorecard-body")).toContainText(String(scorecard.aggregate));
  await expect(page.getByTestId("maker-review-scorecard-body")).toContainText("maturity");
});
