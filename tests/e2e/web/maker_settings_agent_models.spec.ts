import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("settings agent and models bindings grid", async ({ page }) => {
  await page.route("**/v1/platform/model-bindings/defaults**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          defaults: { version: 1, roles: {} },
          roles: [
            { agent_role: "planner", display_name: "Planner", kind: "builtin", binding: null },
            { agent_role: "backend_writer", display_name: "Backend Writer", kind: "builtin", binding: null },
          ],
          providers: [
            { id: "ollama", kind: "local", label: "Ollama" },
            { id: "openai", kind: "cloud", label: "OpenAI API" },
          ],
        }),
      });
      return;
    }
    if (route.request().method() === "PUT") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ defaults: { version: 1, roles: {} } }),
      });
      return;
    }
    return route.continue();
  });
  await page.route("**/v1/settings/me**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ stored: {} }) }),
  );
  await page.route("**/v1/settings/catalog**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ groups: {} }) }),
  );
  await page.route("**/v1/platform/routing-presets**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ active_preset_id: "local_only", presets: [], cloud_preflight: {} }),
    }),
  );
  await page.route("**/v1/platform/hardware**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ profile: { tier: "mid" }, resource_governor: { hardware_tier: "mid" } }),
    }),
  );
  await page.route("**/v1/platform/autopilot/user-profiles**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ profiles: [] }) }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/settings");

  await expect(page.getByTestId("maker-settings-agent-models")).toBeVisible();
  await expect(page.getByTestId("maker-settings-agent-row-planner")).toBeVisible();
  await page.getByTestId("maker-settings-agent-models-save").click();
});
