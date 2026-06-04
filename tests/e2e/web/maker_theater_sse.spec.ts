import { test, expect } from "@playwright/test";

test("maker static includes sse client", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  const html = await page.content();
  expect(html).toMatch(/sse-client|progress/i);
});
