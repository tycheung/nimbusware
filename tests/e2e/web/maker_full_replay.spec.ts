import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("campaign progress and launch scorecard full UI replay", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-full-replay-${Date.now()}`,
      workspace_path: fixtureWorkspace,
      template: "attach",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id as string;

  const campaign = await request.post("/v1/campaigns", {
    headers,
    data: {
      project_id: projectId,
      requirements: {
        business_prompt: "Build a minimal CRM with user authentication and contact list",
      },
      autonomous: true,
      workflow_profile: "campaign_micro_slice",
    },
  });
  expect(campaign.ok()).toBeTruthy();
  const runId = (await campaign.json()).run_id as string;

  await expect
    .poll(
      async () => {
        const progress = await request.get(`/v1/runs/${runId}/maker-progress?simple=true`);
        if (!progress.ok()) return 0;
        const body = await progress.json();
        return Number(body.campaign_progress?.slices_total ?? 0);
      },
      { timeout: 60_000 },
    )
    .toBeGreaterThan(0);

  const launchEval = await request.post(`/v1/runs/${runId}/maker/launch-eval`);
  expect(launchEval.ok()).toBeTruthy();
  const scorecard = await launchEval.json();
  expect(scorecard.aggregate).toBeGreaterThan(0);
  expect(scorecard.attach_context?.prompt_id).toBe("basic_crm");

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");
  await expect(page.locator("#slice-summary")).toContainText("slices", { timeout: 15_000 });

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await activateMakerRoute(page, "/review");
  await expect(page.getByTestId("maker-review-launch-scorecard")).toBeVisible();
  const timelineResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/runs/${runId}/timeline`) && resp.ok(),
  );
  await page.getByTestId("maker-review-launch-scorecard").click();
  await timelineResponse;
  await expect(page.getByTestId("maker-review-scorecard-body")).toContainText(String(scorecard.aggregate));
});
