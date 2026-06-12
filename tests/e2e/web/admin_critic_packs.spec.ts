import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin config critic packs tab lists packs from API", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const listed = await request.get("/v1/config/critic-packs", { headers });
  expect(listed.ok()).toBeTruthy();
  const packIds = ((await listed.json()).pack_ids || []) as string[];
  expect(packIds.length).toBeGreaterThan(0);

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto("/v1/admin/app/config");
  await page.getByRole("button", { name: "Critic packs" }).click();
  await expect(page.getByRole("heading", { name: "Critic packs" })).toBeVisible();
  await expect(page.locator("select")).toContainText(packIds[0], { timeout: 15_000 });
  await expect(page.getByRole("textbox", { name: "Content (JSON)" })).toHaveValue(/domain/, {
    timeout: 15_000,
  });

  const workflows = await request.get(`/v1/config/critic-packs/${packIds[0]}/workflows`, {
    headers,
  });
  expect(workflows.ok()).toBeTruthy();
  const body = await workflows.json();
  expect(Array.isArray(body.workflow_profiles)).toBeTruthy();
});
