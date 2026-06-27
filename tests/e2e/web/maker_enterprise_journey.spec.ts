import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("enterprise home shell shows fleet links and hides factory hero", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
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
  await page.route("**/v1/platform/fleet-governance**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        setup_bundle: "enterprise",
        mandatory_discovery: true,
        default_surfaces: ["web", "api"],
        deploy_chain_required: true,
        allowed_deploy_targets: ["aws-ecs", "aws-static-site", "github-actions"],
        enforcement_policy: { min_enforcement_level: 4, max_enforcement_level: 8 },
      }),
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

  await page.addInitScript(() => {
    localStorage.setItem("maker_archetype_subchoice", "enterprise");
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/home");

  await expect(page.getByTestId("maker-home-enterprise")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-home-enterprise-fleet")).toBeVisible();
  await expect(page.getByTestId("maker-home-deploy-allowlist")).toContainText("aws-ecs");
  await expect(page.getByTestId("maker-home-guided-campaign")).toBeHidden();
});
