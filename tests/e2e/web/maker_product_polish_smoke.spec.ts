import { test, expect, type Page } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const SESSION_ID = "00000000-0000-4000-8000-000000000401";
const PROJECT_ID = "00000000-0000-4000-8000-000000000402";

function mockProjects(page: Page) {
  return page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Polish", workspace_path: "/tmp/ws" }],
      }),
    }),
  );
}

function sessionPayload(turns: unknown[] = []) {
  return {
    session_id: SESSION_ID,
    project_id: PROJECT_ID,
    turns,
  };
}

function mockPlatform(page: Page) {
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
    if (url.includes("/safe-coding-preferences")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ industry_critic_pack_ids: [] }),
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

function mockChatSession(page: Page, discoverBody: Record<string, unknown>) {
  return page.route("**/v1/chat/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    if (method === "POST" && url.endsWith("/chat/sessions")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(sessionPayload()),
      });
    }
    if (method === "GET" && url.includes(SESSION_ID)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(
          sessionPayload([{ turn_id: "t1", role: "user", text: "Build a todo app" }]),
        ),
      });
    }
    if (method === "POST" && url.includes("/turns")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          classification: {
            suggested_profile: "campaign_fullstack",
            work_type: "campaign",
            confidence: 0.92,
          },
        }),
      });
    }
    if (method === "POST" && url.includes("/scope/discover")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ scope: discoverBody }),
      });
    }
    return route.continue();
  });
}

test.describe("fo2330–fo2338 product polish smoke (fo2349)", () => {
  test("fo2330 discovery Explain control", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "safe_coding"));
    await mockProjects(page);
    await mockChatSession(page, {
      discovery_complete: false,
      questions_emitted: [
        {
          id: "client_form",
          question: "What kind of client do you want?",
          hint: "Web app runs in the browser; mobile is web-first responsive.",
        },
      ],
      answers: [],
    });

    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await page.getByTestId("maker-chat-project-select").selectOption(PROJECT_ID);
    await page.getByTestId("maker-chat-message").fill("Build a todo app");
    await page.getByTestId("maker-chat-start").click();
    await expect(page.getByTestId("maker-chat-discovery-card")).toBeVisible({ timeout: 15_000 });
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
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "safe_coding"));
    await mockPlatform(page);
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/settings");
    await expect(page.getByTestId("maker-settings-safe-coding")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("maker-settings-industry-critic-pack")).toBeVisible();
  });

  test("fo2338 solo hat chips in chat composer", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "engineer"));
    await mockProjects(page);
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await expect(page.getByTestId("maker-chat-solo-hat-chips")).toBeVisible();
  });

  test("fo2155 scope manifest surface bindings preview", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("maker_archetype_subchoice", "engineer"));
    await mockProjects(page);
    await mockChatSession(page, {
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
    });
    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");
    await page.getByTestId("maker-chat-project-select").selectOption(PROJECT_ID);
    await page.getByTestId("maker-chat-message").fill("Full stack todo");
    await page.getByTestId("maker-chat-start").click();
    await expect(page.getByTestId("maker-chat-scope-manifest")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("maker-chat-scope-surface-bindings")).toBeVisible();
  });
});
