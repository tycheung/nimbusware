import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const SESSION_ID = "pw-chat-override-session";
const RUN_ID = "00000000-0000-4000-8000-000000000002";
const PROJECT_ID = "00000000-0000-4000-8000-000000000098";

test("chat tab operator override skips classifier auto-start", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Override fixture", workspace_path: "/tmp" }],
      }),
    }),
  );

  await page.route("**/v1/chat/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ session_id: SESSION_ID }),
    });
  });

  await page.route("**/v1/chat/classify", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        classification: {
          work_type: "patch",
          confidence: 0.88,
          rationale: "Bug-fix keywords",
          signals: ["keyword:fix"],
          suggested_profile: "patch",
        },
      }),
    });
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/start`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.work_type).toBe("slice");
    expect(body.work_type_source).toBe("operator_override");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID }),
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");
  await expect(page.locator("#view-chat")).toBeVisible();

  await page.getByTestId("maker-chat-work-type-select").selectOption("slice");
  await page.getByTestId("maker-chat-message").fill("Add a small feature to the settings page");
  await page.getByTestId("maker-chat-start").click();

  await expect(page).toHaveURL(new RegExp(`run_id=${RUN_ID.replace(/-/g, "\\-")}`), {
    timeout: 10_000,
  });
});

test("chat classifier override chip uses selected work type", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Override fixture", workspace_path: "/tmp" }],
      }),
    }),
  );

  await page.route("**/v1/chat/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ session_id: SESSION_ID }),
    });
  });

  await page.route("**/v1/chat/classify", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        classification: {
          work_type: "patch",
          confidence: 0.75,
          rationale: "Looks like a quick fix",
          signals: ["keyword:fix"],
          suggested_profile: "patch",
        },
      }),
    });
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/start`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.work_type).toBe("campaign");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID }),
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");

  await page.getByTestId("maker-chat-message").fill("Build a full CRM for sales team");
  await page.getByTestId("maker-chat-start").click();

  await expect(page.getByTestId("maker-chat-classifier-card")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("maker-chat-override-chip-campaign").click();

  await expect(page).toHaveURL(new RegExp(`run_id=${RUN_ID.replace(/-/g, "\\-")}`), {
    timeout: 10_000,
  });
});
