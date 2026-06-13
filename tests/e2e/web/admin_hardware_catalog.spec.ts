import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin hardware page shows model catalog info strip", async ({ page }) => {
  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);

  await page.route("**/v1/platform/models/catalog-info", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        version: 3,
        model_count: 42,
        updated_at: "2026-06-01T00:00:00Z",
        source: "bundled",
      }),
    }),
  );

  await page.goto("/v1/admin/app/hardware");
  const strip = page.getByTestId("admin-catalog-info");
  await expect(strip).toBeVisible({ timeout: 10_000 });
  await expect(strip).toContainText("v3");
  await expect(strip).toContainText("42 models");
  await expect(strip).toContainText("bundled");
});
