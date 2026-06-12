import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin nav pages load preflight metrics hardware and agents", async ({ page }) => {
  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);

  await page.goto("/v1/admin/app/preflight");
  await expect(page.getByRole("heading", { name: "Preflight history" })).toBeVisible();

  await page.goto("/v1/admin/app/metrics");
  await expect(page.getByRole("heading", { name: "Competitive metrics" })).toBeVisible();

  await page.goto("/v1/admin/app/hardware");
  await expect(page.getByRole("heading", { name: "Hardware" })).toBeVisible();

  await page.goto("/v1/admin/app/agents");
  await expect(page.getByRole("heading", { name: "Custom agents" })).toBeVisible();
});
