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

  await page.route("**/v1/chat/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ session_id: SESSION_ID }),
    });
  });

  await page.route("**/v1/chat/classify", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.message).toContain("failing test");
    expect(body.attachments).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          failing_test: "tests/test_login.py::test_bad",
          stack_trace: "AssertionError",
        }),
      ]),
    );
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
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
      body: JSON.stringify({ run_id: RUN_ID }),
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

  await expect(page).toHaveURL(new RegExp(`run_id=${RUN_ID.replace(/-/g, "\\-")}`), {
    timeout: 10_000,
  });
});
