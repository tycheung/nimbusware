import path from "node:path";
import { test, expect } from "@playwright/test";
import { adminToken } from "./playwright_seed";

const repoRoot = path.resolve(process.cwd(), "../../..");
const fixtureWorkspace = `${repoRoot}/tests/fixtures/repos/tiny_python_app`.replace(/\\/g, "/");

test("admin research approve posts approve endpoint", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-admin-research-${Date.now()}`,
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
      requirements: { business_prompt: "Admin research approve" },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  const runId = (await runResp.json()).run_id as string;
  const briefId = "brief-pw-1";

  await page.route(`**/v1/runs/${runId}/research`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        briefs: [
          {
            brief_id: briefId,
            brief_kind: "domain",
            status: "draft",
            review_status: "pending",
            summary: "Operator brief",
          },
        ],
      }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/research/${briefId}/approve`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ brief_id: briefId, review_status: "approved" }),
    }),
  );

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto(`/v1/admin/app/runs/${runId}`);

  await expect(page.getByRole("heading", { name: "Research briefs" })).toBeVisible({ timeout: 15_000 });
  const approvePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/research/${briefId}/approve`) &&
      resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Approve" }).first().click();
  expect((await approvePromise).ok()).toBeTruthy();
});

test("admin ollama pull posts pull request", async ({ page }) => {
  await page.route("**/v1/admin/ollama/pull", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    }),
  );
  await page.route("**/v1/admin/ollama/tags**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ models: [] }),
    }),
  );

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto("/v1/admin/app/config");

  await page.getByRole("button", { name: "Ollama" }).click();
  await expect(page.getByRole("button", { name: "Pull" })).toBeVisible({ timeout: 15_000 });
  await page.locator('label:has-text("Pull model") input').fill("llama3.1:8b");
  const pullPromise = page.waitForResponse(
    (resp) => resp.url().includes("/v1/admin/ollama/pull") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Pull" }).click();
  expect((await pullPromise).ok()).toBeTruthy();
});
