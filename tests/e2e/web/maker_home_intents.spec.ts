import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("home intent cards and factory hero demos route to chat", async ({ page }) => {
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
      body: JSON.stringify({ models: [{ model_id: "llama3", label: "Llama 3" }], profile_tier: "mid" }),
    }),
  );
  await page.route("**/v1/platform/readiness**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: "ready", checks: {} }),
    }),
  );
  await page.route("**/v1/platform/onboarding**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ onboarded: true }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/home");

  await expect(page.getByTestId("maker-home-intents")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-intent-patch")).toBeVisible();
  await expect(page.getByTestId("maker-intent-slice")).toBeVisible();
  await expect(page.getByTestId("maker-intent-factory")).toBeVisible();

  await page.getByTestId("maker-intent-patch").click();
  await expect(page).toHaveURL(/#\/chat\?intent=patch/);

  await activateMakerRoute(page, "/home");
  await expect(page.getByTestId("maker-factory-demo-todo")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("maker-factory-demo-crm")).toBeVisible();
  await expect(page.getByTestId("maker-factory-demo-contacts")).toBeVisible();

  await page.getByTestId("maker-factory-demo-todo").click();
  await expect(page).toHaveURL(/#\/chat\?intent=factory/);
  await expect(page).toHaveURL(/prompt=/);
});
