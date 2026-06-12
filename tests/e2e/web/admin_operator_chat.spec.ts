import { test, expect } from "@playwright/test";

const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

test("admin operator chat shows classifier card and accepts patch", async ({ page }) => {
  await page.route("**/v1/admin/ui/operator-chat/message", async (route) => {
    const body = route.request().postDataJSON() as { text?: string };
    if (body.text?.startsWith("/run")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          reply: "Started run `run-1` with profile `patch`.",
          last_run_id: "run-1",
          classification: null,
        }),
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        reply: "Suggested patch → `patch` (92%). Use `/run auto` to start.",
        last_run_id: "",
        classification: {
          work_type: "patch",
          confidence: 0.92,
          rationale: "Failing test detected",
        },
      }),
    });
  });

  await page.addInitScript((token) => {
    sessionStorage.setItem("nimbusware_admin_token", token);
  }, adminToken);

  await page.goto("/v1/admin/app/chat");
  await page.getByRole("textbox").fill("fix failing auth test");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByTestId("admin-chat-classifier-card")).toBeVisible();
  await expect(page.getByTestId("admin-chat-accept-chip")).toBeVisible();
  await page.getByTestId("admin-chat-accept-chip").click();
  await expect(page.getByText("Started run")).toBeVisible();
});
