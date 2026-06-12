import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin fleet tab shows critic reliability and compare controls", async ({ page }) => {
  await page.route("**/v1/admin/app/bootstrap.json", async (route) => {
    const body = await route.fetch().then((r) => r.json());
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ...body,
        edition: "enterprise",
        features: { ...(body.features || {}), enterprise_fleet_ui: true },
      }),
    });
  });
  await page.route("**/v1/enterprise/tenants", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        tenants: [
          { tenant_id: "t-a", slug: "tenant-a", display_name: "Tenant A" },
          { tenant_id: "t-b", slug: "tenant-b", display_name: "Tenant B" },
        ],
      }),
    });
  });
  await page.route("**/v1/admin/ui/enterprise/fleet-dashboard**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        critic_reliability_caption: "Fleet critic reliability",
        critic_reliability_rows: [{ metric: "pass_rate", value: "0.92" }],
        export_json: "{}",
      }),
    });
  });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
    sessionStorage.setItem("nimbusware_enterprise_api_key", "pw-enterprise-test-key");
  }, adminToken);
  await page.goto("/v1/admin/app/fleet");

  await expect(page.getByRole("heading", { name: "Enterprise fleet" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Critic reliability" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cross-tenant comparison" })).toBeVisible();
});
