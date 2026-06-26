import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("enterprise install journey shows audit export and strict chips", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: "p1", name: "Ent", workspace_path: "/tmp/ws" }],
      }),
    }),
  );
  await page.route("**/v1/platform/hardware**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ tier: "mid", ram_available_gb: 16, gpus: [] }),
    }),
  );
  await page.route("**/v1/platform/models/ranked**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ models: [], profile_tier: "mid" }),
    }),
  );
  await page.route("**/v1/platform/readiness**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        checks: {},
        setup_bundle: "enterprise",
        edition: "enterprise",
      }),
    }),
  );
  await page.route("**/v1/platform/onboarding**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ onboarded: true }),
    }),
  );
  await page.route("**/v1/enterprise/compliance/summary**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        gate_pass_rate: 0.92,
        mean_slices_per_run: 2.1,
        audit_retention_days: 90,
      }),
    }),
  );
  await page.route("**/v1/enterprise/audit-export**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ version: 1, iam_actions: [], events: [] }),
    }),
  );

  await page.addInitScript(() => {
    localStorage.setItem("maker_archetype_subchoice", "enterprise");
    window.__NIMBUSWARE__ = { ...(window.__NIMBUSWARE__ || {}), setup_bundle: "enterprise" };
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/home");
  await expect(page.getByTestId("maker-home-enterprise")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-home-enterprise-compliance")).toHaveAttribute(
    "href",
    /panel=compliance/,
  );

  await activateMakerRoute(page, "/review");
  await page.evaluate(() => {
    sessionStorage.setItem("maker_active_run_id", "11111111-1111-4111-8111-111111111111");
  });
  await page.reload();
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");
  const fleetAudit = page.getByTestId("maker-review-fleet-audit-export");
  await expect(fleetAudit).toBeVisible({ timeout: 15_000 });
});
