import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";
const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = path
  .join(repoRoot, "tests", "fixtures", "repos", "tiny_python_app")
  .replace(/\\/g, "/");

test("maker shell loads theater css and session hub module", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  const links = await page.locator('link[rel="stylesheet"]').evaluateAll((els) =>
    els.map((el) => (el as HTMLLinkElement).href),
  );
  expect(links.some((href) => href.includes("theater.css"))).toBeTruthy();

  const hasSessionHub = await page.evaluate(async () => {
    try {
      const mod = await import("/v1/maker/app/js/session-hub.js");
      return typeof mod.resolveRunId === "function";
    } catch {
      return false;
    }
  });
  expect(hasSessionHub).toBeTruthy();
});

test("progress tab shows findings workspace for active run", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-findings-${Date.now()}`,
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
      requirements: { business_prompt: "Playwright findings workspace" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;

  const findingsResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/runs/${runId}/findings`) && resp.ok(),
  );
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");
  await findingsResponse;

  await expect(page.getByTestId("maker-findings-workspace")).toBeVisible();
  await expect(page.getByTestId("maker-findings-empty")).toBeVisible({ timeout: 15_000 });
});
