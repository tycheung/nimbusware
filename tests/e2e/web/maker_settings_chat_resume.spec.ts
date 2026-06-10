import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("settings chat resume toggle clears stored session", async ({ page }) => {
  await page.route("**/v1/settings/**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ stored: {}, values: {} }),
    }),
  );
  await page.route("**/v1/platform/**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ onboarded: true, profile: {}, resource_governor: {} }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");

  await page.evaluate(() => {
    localStorage.setItem("maker_chat_resume_session", "1");
    sessionStorage.setItem("maker_chat_session_id", "resume-test-session");
  });

  await activateMakerRoute(page, "/settings");
  await expect(page.getByTestId("maker-settings-chat-resume")).toBeChecked();

  await page.getByTestId("maker-settings-chat-resume").uncheck();
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem("maker_chat_resume_session")))
    .toBe("0");
  await expect
    .poll(async () => page.evaluate(() => sessionStorage.getItem("maker_chat_session_id")))
    .toBeNull();
});
