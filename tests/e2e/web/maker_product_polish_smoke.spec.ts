import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const repoRoot = path.resolve(process.cwd(), "../../..");
const SESSION_ID = "00000000-0000-4000-8000-000000000401";

function mockPlatform(page: import("@playwright/test").Page) {
  return page.route("**/v1/platform/**", (route) => {
    const url = route.request().url();
    if (url.includes("/industry-critic-packs")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          packs: [
            { id: "fintech", label: "Fintech" },
            { id: "healthcare", label: "Healthcare" },
          ],
        }),
      });
    }
    if (url.includes("/invite-templates")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          templates: [{ id: "fullstack", label: "Full-stack squad", disciplines: ["frontend", "backend"] }],
        }),
      });
    }
    if (url.includes("/onboarding")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ onboarded: true }),
      });
    }
    return route.continue();
  });
}

test.describe("fo2330–fo2338 product polish smoke (fo2349)", () => {
  test("fo2330 discovery Explain control", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "safe_coding"));
    await page.route("**/v1/projects**", (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ projects: [] }) }),
    );
    await page.route("**/v1/chat/**", async (route) => {
      const url = route.request().url();
      const method = route.request().method();
      if (method === "POST" && url.endsWith("/chat/sessions")) {
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({ session_id: SESSION_ID, turns: [] }),
        });
      }
      if (method === "POST" && url.includes("/scope/discover")) {
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            scope: {
              discovery_complete: false,
              questions_emitted: [
                {
                  id: "client_form",
                  question: "What kind of client do you want?",
                  hint: "Web app runs in the browser; mobile is web-first responsive.",
                },
              ],
            },
          }),
        });
      }
      return route.continue();
    });

    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await page.getByTestId("maker-chat-message").fill("Build a todo app");
    await page.getByTestId("maker-chat-start").click();
    await expect(page.getByTestId("maker-chat-discovery-explain-client_form")).toBeVisible();
  });

  test("fo2332 manager scope panel", async ({ page }) => {
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/scope");
    await expect(page.getByTestId("maker-manager-scope-panel")).toBeVisible();
    await expect(page.getByTestId("maker-manager-scope-load")).toBeVisible();
  });

  test("fo2333 industry pack catalog in settings", async ({ page }) => {
    await mockPlatform(page);
    await page.route("**/v1/settings/me**", (route) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ industry_critic_pack_ids: [] }),
      }),
    );
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/settings");
    await expect(page.getByTestId("maker-settings-industry-critic-pack")).toBeVisible();
  });

  test("fo2338 solo hat chips in chat composer", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "engineer"));
    await page.route("**/v1/projects**", (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ projects: [] }) }),
    );
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await expect(page.getByTestId("maker-chat-solo-hat-chips")).toBeVisible();
  });

  test("fo2155 scope manifest surface bindings preview", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "engineer"));
    await page.route("**/v1/projects**", (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ projects: [] }) }),
    );
    await page.route("**/v1/chat/**", async (route) => {
      const url = route.request().url();
      if (route.request().method() === "POST" && url.includes("/scope/discover")) {
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            scope: {
              discovery_complete: true,
              stack_manifest: {
                surfaces: ["web", "api"],
                stacks: { web: "react_vite", api: "fastapi_python" },
                frozen: true,
                version: 1,
              },
              surface_bindings: [
                { surface_id: "web", writer_role: "frontend_writer", model_id: "gpt-test", provider_id: "openai" },
                { surface_id: "api", writer_role: "backend_writer", model_id: "gpt-test", provider_id: "openai" },
              ],
            },
          }),
        });
      }
      return route.continue();
    });
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await page.getByTestId("maker-chat-message").fill("Full stack todo");
    await page.getByTestId("maker-chat-start").click();
    await expect(page.getByTestId("maker-chat-scope-surface-bindings")).toBeVisible();
  });
});
