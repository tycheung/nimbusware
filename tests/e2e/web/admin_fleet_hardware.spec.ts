import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin fleet tab renders hardware host rows", async ({ page }) => {
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
  await page.route("**/v1/enterprise/tenants", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ tenants: [] }),
    }),
  );
  await page.route("**/v1/admin/ui/enterprise/fleet-dashboard**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        hardware_rows: [
          {
            host: "worker-01",
            tier: "strong",
            ram_available_gb: 48,
            ram_total_gb: 64,
            gpu_count: 2,
            platform: "linux",
            errors: "",
          },
        ],
        export_json: "{}",
      }),
    });
  });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
    sessionStorage.setItem("nimbusware_enterprise_api_key", "pw-enterprise-test-key");
  }, adminToken);
  await page.goto("/v1/admin/app/fleet");

  await expect(page.getByRole("heading", { name: "Hardware fleet" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "worker-01" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "strong" })).toBeVisible();
});

test("admin fleet rescan button refreshes hardware rows", async ({ page }) => {
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
  await page.route("**/v1/enterprise/tenants", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ tenants: [] }),
    }),
  );
  await page.route("**/v1/admin/ui/enterprise/fleet-dashboard**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        hardware_rows: [{ host: "worker-old", tier: "medium", gpu_count: 0, errors: "" }],
        export_json: "{}",
      }),
    }),
  );
  await page.route("**/v1/platform/hardware/fleet/rescan", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        hosts: [{ host: "worker-new", tier: "strong", gpu_count: 2, errors: "" }],
      }),
    });
  });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
    sessionStorage.setItem("nimbusware_enterprise_api_key", "pw-enterprise-test-key");
  }, adminToken);
  await page.goto("/v1/admin/app/fleet");

  await page.getByTestId("admin-fleet-rescan-btn").click();
  await expect(page.getByRole("cell", { name: "worker-new" })).toBeVisible({ timeout: 10_000 });
});

test("admin fleet legal hold toggle saves audit policy", async ({ page }) => {
  let legalHold = false;
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
  await page.route("**/v1/enterprise/tenants", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ tenants: [] }),
    }),
  );
  await page.route("**/v1/admin/ui/enterprise/fleet-dashboard**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ hardware_rows: [], export_json: "{}" }),
    }),
  );
  await page.route("**/v1/enterprise/compliance/summary**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        audit_policy: { legal_hold: legalHold },
        gate_pass_rate: 0.9,
      }),
    }),
  );
  await page.route("**/v1/enterprise/audit-policy**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ legal_hold: legalHold, redaction_patterns: [] }),
      });
      return;
    }
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON() as { legal_hold?: boolean };
      legalHold = Boolean(body.legal_hold);
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ legal_hold: legalHold, redaction_patterns: [] }),
      });
      return;
    }
    await route.continue();
  });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
    sessionStorage.setItem("nimbusware_enterprise_api_key", "pw-enterprise-test-key");
  }, adminToken);
  await page.goto("/v1/admin/app/fleet");

  await expect(page.getByTestId("admin-fleet-audit-policy")).toBeVisible({ timeout: 15_000 });
  const putPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes("/v1/enterprise/audit-policy") && resp.request().method() === "PUT",
  );
  await page.getByTestId("admin-fleet-legal-hold-toggle").click();
  const putResp = await putPromise;
  expect(putResp.ok()).toBeTruthy();
  await expect(page.getByTestId("admin-fleet-legal-hold-toggle").locator("input")).toBeChecked();
});
