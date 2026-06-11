import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("settings tab applies hybrid routing preset from UI", async ({ page }) => {
  await page.route("**/v1/platform/routing-presets**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          active_preset_id: "local_only",
          presets: [
            { id: "local_only", label: "Local only" },
            { id: "local_cloud_critique", label: "Local + cloud critique" },
          ],
          cloud_preflight: { ok: false, message: "cloud disabled" },
        }),
      });
      return;
    }
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { preset_id?: string };
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          preset_id: body.preset_id,
          cloud_enabled: body.preset_id !== "local_only",
          cloud_preflight: { ok: false },
        }),
      });
      return;
    }
    return route.continue();
  });
  await page.route("**/v1/settings/me**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ stored: {} }),
    }),
  );
  await page.route("**/v1/settings/catalog**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ groups: {} }) }),
  );
  await page.route("**/v1/platform/hardware**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ profile: { tier: "mid" }, resource_governor: { hardware_tier: "mid" } }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/settings");

  await expect(page.getByTestId("maker-settings-routing-presets")).toBeVisible();
  await expect(page.getByTestId("maker-settings-routing-active")).toContainText("local_only");
  await page.getByTestId("maker-settings-routing-select").selectOption("local_cloud_critique");
  await page.getByTestId("maker-settings-routing-apply").click();
  await expect(page.getByTestId("maker-settings-routing-active")).toBeVisible();
});
