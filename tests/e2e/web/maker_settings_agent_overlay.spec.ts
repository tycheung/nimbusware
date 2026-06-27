import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("settings agent overlay editor saves per discipline", async ({ page }) => {
  let savedBody: Record<string, unknown> | null = null;

  await page.route("**/v1/users/me/agent-overlays**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "GET" && url.endsWith("/agent-overlays")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "user-1",
          overlays: {},
          disciplines: [
            { id: "backend", display_name: "Backend", taxonomy_key: "backend_writer" },
            { id: "frontend", display_name: "Frontend", taxonomy_key: "frontend_writer" },
          ],
        }),
      });
      return;
    }
    if (route.request().method() === "PUT" && url.includes("/agent-overlays/backend")) {
      savedBody = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "user-1",
          overlays: {
            backend: {
              prompt_extension: savedBody?.prompt_extension,
              custom_agent_id: savedBody?.custom_agent_id,
            },
          },
        }),
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
  await page.route("**/v1/platform/model-bindings/defaults**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ defaults: { version: 1, roles: {} }, roles: [], providers: [] }),
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
  await page.route("**/v1/platform/enforcement/user-profiles**", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ profiles: [] }) }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/settings");

  await expect(page.getByTestId("maker-settings-agent-overlays")).toBeVisible();
  await page.getByTestId("maker-settings-agent-overlay-discipline").selectOption("backend");
  await page.getByTestId("maker-settings-agent-overlay-prompt").fill("Prefer FastAPI idioms.");
  await page.getByTestId("maker-settings-agent-overlay-save").click();

  await expect.poll(() => savedBody?.prompt_extension).toBe("Prefer FastAPI idioms.");
});
