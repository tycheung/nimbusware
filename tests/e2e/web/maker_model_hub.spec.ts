import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("model hub shows local and API connection sections", async ({ page }) => {
  await page.route("**/v1/platform/ollama/models**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        reachable: false,
        base_url: "http://127.0.0.1:11434",
        primary_model_id: null,
        fallback_model_ids: [],
        user_policy: { allow_pull: true, allow_delete: true, allow_update_routing: true },
        models: [],
      }),
    }),
  );
  await page.route("**/v1/platform/provider-presets**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        providers: [
          { id: "openai", kind: "cloud", label: "OpenAI API", connection_kind: "api_key" },
          { id: "google", kind: "cloud", label: "Google Gemini", connection_kind: "api_key" },
        ],
      }),
    }),
  );
  await page.route("**/v1/platform/provider-connections**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ connections: [] }),
      });
    }
    return route.continue();
  });
  await page.route("**/v1/platform/models/ranked**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ models: [] }),
    }),
  );
  await page.route("**/v1/platform/hardware**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ profile: { tier: "mid", gpus: [] } }),
    }),
  );
  await page.route("**/v1/platform/models/catalog-info**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ model_count: 0, version: 1 }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/models");

  await expect(page.getByTestId("maker-model-hub")).toBeVisible();
  await expect(page.getByTestId("maker-model-hub-local")).toBeVisible();
  await expect(page.getByTestId("maker-ollama-install")).toBeVisible();
  await page.getByRole("button", { name: "API connections" }).click();
  await expect(page.getByTestId("maker-model-hub-api")).toBeVisible();
  await expect(page.getByTestId("maker-provider-card-openai")).toBeVisible();
  await expect(page.getByTestId("maker-cursor-card")).toBeVisible();
});
