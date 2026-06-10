import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const SESSION_ID = "pw-chat-patch-session";
const RUN_ID = "00000000-0000-4000-8000-000000000001";
const PROJECT_ID = "00000000-0000-4000-8000-000000000099";

test("chat tab patch flow creates session, classifies, and starts", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Patch fixture", workspace_path: "/tmp" }],
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
    if (route.request().method() === "GET" && url.includes(SESSION_ID)) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          project_id: PROJECT_ID,
          messages: [{ role: "user", text: "Fix the failing test", turn_id: "turn-1" }],
        }),
      });
      return;
    }
    if (url.includes("/graph")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ session_id: SESSION_ID, nodes: [], edges: [], branches: [] }),
      });
      return;
    }
    return route.continue();
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/turns`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.text).toContain("failing test");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        message: { role: "user", text: body.text, turn_id: "turn-1" },
        classification: {
          work_type: "patch",
          confidence: 0.92,
          rationale: "Failing test and stack trace detected",
          signals: ["failing_test", "stack_trace"],
          suggested_profile: "patch",
        },
      }),
    });
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/start`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.work_type).toBe("patch");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: RUN_ID,
        turn: { role: "run_status", text: "Started patch run (patch).", turn_id: "turn-2" },
      }),
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");
  await expect(page.locator("#view-chat")).toBeVisible();
  await expect(page.getByTestId("maker-chat-start")).toBeVisible();

  await page.getByTestId("maker-chat-message").fill("Fix the failing test in login flow");
  await page.getByTestId("maker-chat-failing-test").fill("tests/test_login.py::test_bad");
  await page.getByTestId("maker-chat-stack-trace").fill("AssertionError");
  await page.getByTestId("maker-chat-start").click();

  await expect(page.getByTestId("maker-chat-classifier-card")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("maker-chat-classifier-card")).toContainText("Patch");
  await page.getByTestId("maker-chat-accept-chip").click();

  await expect(page).toHaveURL(new RegExp(`#/chat.*run_id=${RUN_ID.replace(/-/g, "\\-")}`), {
    timeout: 10_000,
  });
});
