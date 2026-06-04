import { test, expect } from "@playwright/test";

test("maker bootstrap exposes api_base", async ({ request }) => {
  const res = await request.get("/v1/maker/app/bootstrap.json");
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(String(body.api_base || "")).toContain("/v1");
});
