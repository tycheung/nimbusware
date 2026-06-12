import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin config tabs load bundles blast radius and personas", async ({ page }) => {
  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);
  await page.goto("/v1/admin/app/config");

  await page.getByRole("button", { name: "Bundles" }).click();
  await expect(page.getByRole("heading", { name: "Configuration" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();

  await page.getByRole("button", { name: "Blast radius" }).click();
  await expect(page.getByRole("heading", { name: "Workflow edit blast radius" })).toBeVisible();
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.locator(".hint, .error, table.data-table").first()).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("button", { name: "Personas" }).click();
  await expect(page.getByRole("heading", { name: "Scope overlap report" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Probation reliability" })).toBeVisible();

  await page.getByRole("button", { name: "Ollama" }).click();
  await expect(page.getByRole("button", { name: "Pull" })).toBeVisible();
});
