import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("engineer chat shows dismissible solo hat coach hint", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("maker_archetype_subchoice", "engineer");
    localStorage.removeItem("maker_solo_hat_coach_dismissed");
  });
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");

  await expect(page.getByTestId("maker-chat-solo-hat-coach")).toBeVisible();
  await page.getByTestId("maker-chat-solo-hat-coach-dismiss").click();
  await expect(page.getByTestId("maker-chat-solo-hat-coach")).toHaveCount(0);
});

test("safe coding chat hides solo hat coach hint", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("maker_archetype_subchoice", "safe_coding");
    localStorage.removeItem("maker_solo_hat_coach_dismissed");
  });
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");

  await expect(page.getByTestId("maker-chat-solo-hat-coach")).toHaveCount(0);
});
