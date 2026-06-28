import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("engineer chat @ discipline autocomplete inserts routed mention", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("maker_archetype_subchoice", "engineer");
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

  const composer = page.locator("#chat-form").getByTestId("maker-chat-message");
  await composer.fill("@fe");
  await expect(page.locator("#chat-form").getByTestId("maker-chat-mention-menu")).toBeVisible();
  await page.locator("#chat-form").getByTestId("maker-chat-mention-frontend").click();
  await expect(composer).toHaveValue(/@frontend\s/);
});
