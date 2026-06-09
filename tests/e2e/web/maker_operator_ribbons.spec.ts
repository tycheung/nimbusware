import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("progress tab exposes dev-env, interjection, and autopilot ribbons", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-operator-${Date.now()}`,
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
      requirements: { business_prompt: "Operator ribbons" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-dev-env-ribbon")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-dev-env-regression-detail")).toBeVisible();
  await expect(page.getByTestId("maker-dev-env-start")).toBeVisible();
  await expect(page.getByTestId("maker-interjection-ribbon")).toBeVisible();
  await expect(page.getByTestId("maker-interjection-next")).toBeVisible();
  await expect(page.getByTestId("maker-interjection-last")).toBeVisible();
  await expect(page.getByTestId("maker-autopilot-ribbon")).toBeVisible();
  await expect(page.getByTestId("maker-autopilot-slider")).toBeVisible();
  await expect(page.getByTestId("maker-autopilot-save")).toBeVisible();
  await expect(page.getByTestId("maker-learnings-ribbon")).toBeVisible();
  await expect(page.getByTestId("maker-autopilot-profile-select")).toBeVisible();
});

test("interjection ribbon queues next-priority message via UI", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-interject-ui-${Date.now()}`,
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
      requirements: { business_prompt: "Interjection UI" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const input = page.getByTestId("maker-interjection-input");
  await expect(input).toBeVisible({ timeout: 15_000 });
  await input.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByTestId("maker-interjection-next")).toBeFocused();
  await input.fill("Steer from Playwright");
  const queuePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/interjection-queue`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-interjection-next").click();
  await queuePromise;

  const queueResp = await request.get(`/v1/runs/${runId}/interjection-queue`);
  expect(queueResp.ok()).toBeTruthy();
  const items = (await queueResp.json()).queue?.items || [];
  expect(items.some((i: { message?: string }) => i.message === "Steer from Playwright")).toBeTruthy();
});

test("autopilot ribbon applies level via API from UI", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-autopilot-ui-${Date.now()}`,
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
      requirements: { business_prompt: "Autopilot UI" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const slider = page.getByTestId("maker-autopilot-slider");
  await expect(slider).toBeVisible({ timeout: 15_000 });
  await slider.evaluate((el) => {
    (el as HTMLInputElement).value = "8";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const savePromise = page.waitForResponse(
    (resp) => resp.url().includes(`/v1/runs/${runId}/autopilot`) && resp.request().method() === "PUT",
  );
  await page.getByTestId("maker-autopilot-save").click();
  await savePromise;

  const apResp = await request.get(`/v1/runs/${runId}/autopilot`);
  expect(apResp.ok()).toBeTruthy();
  expect((await apResp.json()).level).toBe(8);
});
