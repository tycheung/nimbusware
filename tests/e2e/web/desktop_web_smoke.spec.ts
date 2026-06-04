import { test, expect } from "@playwright/test";

test("maker app shell loads", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  await expect(page.locator("body")).toContainText(/Maker|run-theater/i);
});

test("admin bootstrap json", async ({ request }) => {
  const res = await request.get("/v1/admin/app/bootstrap.json");
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.api_base).toBeTruthy();
});
