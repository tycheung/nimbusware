import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("progress tab exposes save-compaction control", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-artifact-save-${Date.now()}`,
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
      requirements: { business_prompt: "Save compaction artifact control" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-compact-save-artifact")).toBeVisible({ timeout: 15_000 });
});

test("progress tab inserts context artifact from library", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-artifact-insert-${Date.now()}`,
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
      requirements: { business_prompt: "Insert context artifact" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const created = await request.post(`/v1/projects/${projectId}/context-artifacts`, {
    data: {
      title: "Operator note",
      content: "Keep migrations reversible",
      kind: "note",
    },
  });
  expect(created.ok()).toBeTruthy();

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const artifactRow = page.getByTestId("maker-context-artifact").first();
  await expect(artifactRow).toBeVisible({ timeout: 15_000 });

  const insertBtn = page.getByTestId("maker-context-artifact-insert").first();
  await expect(insertBtn).toBeVisible();
  const insertResp = page.waitForResponse(
    (resp) => resp.url().includes("/context-artifacts/") && resp.url().includes("/insert") && resp.request().method() === "POST",
  );
  await insertBtn.click();
  const insertResult = await insertResp;
  expect(insertResult.ok()).toBeTruthy();

  const timeline = await request.get(`/v1/runs/${runId}/timeline`);
  expect(timeline.ok()).toBeTruthy();
  const events = (await timeline.json()).events as Array<{ payload?: { stage_name?: string } }>;
  expect(
    events.some((ev) => ev.payload?.stage_name === "campaign.context.artifact.inserted"),
  ).toBeTruthy();
});
