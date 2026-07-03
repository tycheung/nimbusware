import { test, expect } from "@playwright/test";

test("workspace smoke", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/.+/);
});
