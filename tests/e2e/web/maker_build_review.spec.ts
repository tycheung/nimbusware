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
});
