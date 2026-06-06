import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("build tab module exposes start-run test id", async ({ request }) => {
  const res = await request.get("/v1/maker/app/js/tabs/build.js");
  expect(res.ok()).toBeTruthy();
  const body = await res.text();
  expect(body).toContain('data-testid="maker-build-start-run"');
});

test("review tab module exposes refresh test id", async ({ request }) => {
  const res = await request.get("/v1/maker/app/js/tabs/review.js");
  expect(res.ok()).toBeTruthy();
  const body = await res.text();
  expect(body).toContain('data-testid="maker-review-refresh"');
  expect(body).toContain("maker-review-approve-plan");
  expect(body).toContain("maker-review-apply-slice");
  expect(body).toContain('data-testid="maker-review-launch-scorecard"');
});

test("build tab shows start-run control when route is active", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );
  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/build");
  await expect(page.locator("#view-build")).toBeVisible();
  await expect(page.getByTestId("maker-build-start-run")).toBeVisible();
});

test("review tab shows approval controls when route is active", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");
  await expect(page.locator("#view-review")).toBeVisible();
  await expect(page.getByTestId("maker-review-refresh")).toBeVisible();
  await expect(page.getByTestId("maker-review-launch-scorecard")).toBeVisible();
});
