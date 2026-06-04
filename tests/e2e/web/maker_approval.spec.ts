import { test, expect } from "@playwright/test";

test("maker static includes review tab module", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  const html = await page.content();
  expect(html).toMatch(/review|tabs/i);
});
