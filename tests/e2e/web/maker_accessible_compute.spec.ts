import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("accessible compute drawer opens for session admin", async ({ page }) => {
  const sessionId = "00000000-0000-4000-8000-000000000088";
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [{ project_id: "p1", name: "Demo" }] }),
    }),
  );
  await page.route(`**/v1/chat/sessions/${sessionId}**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        session_id: sessionId,
        project_id: "p1",
        my_participant_role: "session_admin",
        participants: [{ user_id: "u1", role: "session_admin", display_name: "Host" }],
        turns: [],
      }),
    }),
  );
  await page.route(`**/v1/compute/nodes?session_id=${sessionId}**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        nodes: [
          {
            node_id: "00000000-0000-4000-8000-000000000001",
            display_name: "alex-mac",
            status: "online",
            share_policy: "managed_by_host",
            allow_host_resource_management: true,
            capabilities: { claims_total: 4, claims_used: 3 },
          },
        ],
      }),
    }),
  );
  await page.goto(`/v1/maker/app/#/chat?session_id=${sessionId}`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/chat");
  await page.evaluate(() => {
    sessionStorage.setItem("maker_chat_session_id", "00000000-0000-4000-8000-000000000088");
  });
  await page.reload();
  await activateMakerRoute(page, "/chat");
  const trigger = page.getByTestId("maker-accessible-compute-trigger");
  await expect(trigger).toBeVisible({ timeout: 15000 });
  await page.getByTestId("maker-accessible-compute-trigger").click();
  const drawer = page.getByTestId("maker-accessible-compute");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("alex-mac");
  await expect(drawer).toContainText("low headroom");
});
