import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("safe coding wizard shows prepare workspace without terminal copy", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: "p1", name: "Demo", workspace_path: "/tmp/ws" }],
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
      body: JSON.stringify({ status: "ready", checks: {}, setup_bundle: "default" }),
    }),
  );
  await page.route("**/v1/platform/workspace-readiness**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ready: false,
        warnings: ["No tests/e2e folder"],
        plain_summary: "Add browser checks to unlock gates.",
        checks: { e2e_dir: false },
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
    localStorage.setItem("maker_archetype_subchoice", "safe_coding");
    localStorage.removeItem("maker_safe_coding_wizard_done");
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/home");

  const wizard = page.getByTestId("maker-safe-coding-wizard");
  await expect(wizard).toBeVisible({ timeout: 15_000 });
  await expect(wizard).not.toContainText("poetry run");
  await expect(wizard).not.toContainText("playwright install");
  await expect(page.getByTestId("maker-safe-coding-prepare")).toBeVisible();
});
