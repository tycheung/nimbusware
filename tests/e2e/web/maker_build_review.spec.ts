import { test, expect } from "@playwright/test";

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

test("build tab renders start-run control in DOM", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );
  await page.goto("/v1/maker/app/");
  await page.evaluate(async () => {
    const { loadRoute } = await import("/v1/maker/app/js/tab-loader.js");
    await loadRoute("/build");
  });
  await expect(page.locator('#build-mount [data-testid="maker-build-start-run"]')).toBeAttached();
});

test("review tab renders approval controls in DOM", async ({ page }) => {
  await page.goto("/v1/maker/app/");
  await page.evaluate(async () => {
    const root = document.getElementById("review-mount");
    const { mountReview } = await import("/v1/maker/app/js/tabs/review.js");
    await mountReview(root);
  });
  await expect(page.locator('#review-mount [data-testid="maker-review-refresh"]')).toBeAttached();
  await expect(page.locator('#review-mount [data-testid="maker-review-launch-scorecard"]')).toBeAttached();
});
