import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

async function seedRun(request: import("@playwright/test").APIRequestContext) {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-btn-${Date.now()}`,
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
      requirements: { business_prompt: "Button click coverage" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  return (await runResp.json()).run_id as string;
}

test("progress compact all posts compact scope", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const toolbar = page.getByTestId("maker-compact-toolbar");
  await expect(toolbar).toBeVisible({ timeout: 15_000 });
  const compactPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/compact`) && resp.request().method() === "POST",
  );
  await toolbar.getByRole("button", { name: "Compact all" }).click();
  const compactResp = await compactPromise;
  expect(compactResp.ok()).toBeTruthy();
});

test("progress dev env start posts start endpoint", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-dev-env-start")).toBeVisible({ timeout: 15_000 });
  const startPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/dev-env/start`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-dev-env-start").click();
  const startResp = await startPromise;
  expect(startResp.ok()).toBeTruthy();
});

test("progress interjection last queues message", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const input = page.getByTestId("maker-interjection-input");
  await expect(input).toBeVisible({ timeout: 15_000 });
  await input.fill("Last-priority steer");
  const queuePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/interjection-queue`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-interjection-last").click();
  await queuePromise;

  const queueResp = await request.get(`/v1/runs/${runId}/interjection-queue`);
  expect(queueResp.ok()).toBeTruthy();
  const items = (await queueResp.json()).queue?.items || [];
  expect(items.some((i: { message?: string }) => i.message === "Last-priority steer")).toBeTruthy();
});

test("progress finding interject prefills steer message", async ({ page }) => {
  const runId = "00000000-0000-4000-8000-000000000011";
  await page.route(`**/v1/runs/${runId}/maker-progress**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: runId,
        verdict: "blocked",
        gate_summary: { blocked: true, headline: "Gate failed" },
        blocking_findings: [{ severity: "BLOCKER", summary: "Tests failed" }],
      }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/findings**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        findings: [
          {
            event_type: "finding.emitted",
            payload: { severity: "BLOCKER", summary: "Slice gate failed", category: "gate" },
          },
        ],
      }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/theater/stream**`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );
  await page.route(`**/v1/runs/${runId}/maker-progress/stream**`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-finding-action-interject")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("maker-finding-action-interject").click();
  await expect(page.getByTestId("maker-interjection-input")).toHaveValue(/Address: Slice gate failed/);
});

test("review slice diff loads patch text", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.route(`**/v1/runs/${runId}/maker/pending`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ pending: { slice_index: 0 } }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/slices/0/diff`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ patch: "--- a/foo.py\n+++ b/foo.py\n+print('ok')" }),
    }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");

  const advanced = page.getByTestId("maker-review-advanced");
  await expect(advanced).toBeVisible({ timeout: 15_000 });
  await advanced.locator("summary").click();

  await expect(page.getByTestId("maker-review-load-diff")).toBeVisible();
  await page.getByTestId("maker-review-load-diff").click();
  await expect(page.locator("#rev-diff")).toContainText("print('ok')");
});

test("review revert workspace posts revert", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.route(`**/v1/runs/${runId}/workspace/revert`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ reverted: true }),
    }),
  );
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");

  const advanced = page.getByTestId("maker-review-advanced");
  await expect(advanced).toBeVisible({ timeout: 15_000 });
  await advanced.locator("summary").click();

  await expect(page.getByTestId("maker-review-revert")).toBeVisible();
  const revertPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/workspace/revert`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-review-revert").click();
  const revertResp = await revertPromise;
  expect(revertResp.ok()).toBeTruthy();
});

test("progress integrator refresh fetches catalog candidates", async ({ page, request }) => {
  const runId = await seedRun(request);
  await page.route("**/v1/bundles/catalog-candidates**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ candidates: [] }),
    }),
  );
  await page.route("**/v1/bundles/catalog**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ document_version: 1 }),
    }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-integrator-stitch-refresh")).toBeVisible({ timeout: 15_000 });
  const refreshPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes("/v1/bundles/catalog-candidates") && resp.request().method() === "GET",
  );
  await page.getByTestId("maker-integrator-stitch-refresh").click();
  const refreshResp = await refreshPromise;
  expect(refreshResp.ok()).toBeTruthy();
});
