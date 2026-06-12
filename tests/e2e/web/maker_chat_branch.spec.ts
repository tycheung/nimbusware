import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const SESSION_ID = "pw-chat-branch-session";
const PROJECT_ID = "00000000-0000-4000-8000-000000000097";
const TURN_A = "10000000-0000-4000-8000-000000000001";
const TURN_B = "10000000-0000-4000-8000-000000000002";

test("chat fork restores from user turn and shows branch panel", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Branch fixture", workspace_path: "/tmp" }],
      }),
    }),
  );

  await page.route("**/v1/chat/sessions**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "POST" && url.endsWith("/sessions")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ session_id: SESSION_ID, project_id: PROJECT_ID, messages: [] }),
      });
      return;
    }
    if (route.request().method() === "GET" && url.includes(SESSION_ID) && !url.includes("/graph")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          messages: [
            { role: "user", text: "first path", turn_id: TURN_A },
            { role: "user", text: "alternate path", turn_id: TURN_B },
          ],
        }),
      });
      return;
    }
    if (url.includes("/graph")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          branches: [{ parent_turn_id: TURN_A, child_turn_ids: [TURN_A, TURN_B] }],
          nodes: [
            { turn_id: TURN_A, text: "first path", parent_turn_id: null },
            { turn_id: TURN_B, text: "alternate path", parent_turn_id: TURN_A },
          ],
          edges: [{ from_turn_id: TURN_A, to_turn_id: TURN_B }],
        }),
      });
      return;
    }
    if (route.request().method() === "POST" && url.includes("/fork")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          active_leaf_turn_id: TURN_A,
          messages: [{ role: "user", text: "first path", turn_id: TURN_A }],
        }),
      });
      return;
    }
    if (route.request().method() === "PUT" && url.includes("/active-leaf")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          active_leaf_turn_id: TURN_B,
          messages: [{ role: "user", text: "alternate path", turn_id: TURN_B }],
        }),
      });
      return;
    }
    return route.continue();
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/turns`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        message: { role: "user", text: "first path", turn_id: TURN_A },
        classification: { work_type: "patch", confidence: 0.9, suggested_profile: "patch" },
      }),
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");

  await page.getByTestId("maker-chat-message").fill("first path");
  await page.getByTestId("maker-chat-start").click();

  await expect(page.getByTestId(`maker-chat-fork-${TURN_A}`)).toBeVisible({ timeout: 10_000 });
  await page.getByTestId(`maker-chat-fork-${TURN_A}`).click();

  await expect(page.getByTestId("maker-chat-branch-panel")).toBeVisible();
  await page.getByTestId(`maker-chat-branch-${TURN_B}`).click();
  await expect(page.getByText("alternate path")).toBeVisible();
});
