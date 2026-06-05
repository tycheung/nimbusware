import { test, expect } from "@playwright/test";

test("admin app index loads", async ({ page }) => {
  await page.goto("/v1/admin/app/");
  await expect(page.locator("body")).toContainText(/Nimbusware Admin|Loading|Admin sign-in/i);
});
