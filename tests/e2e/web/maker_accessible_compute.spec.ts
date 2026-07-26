import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("accessible compute drawer opens for session admin", async ({ page }) => {
  const sessionId = "00000000-0000-4000-8000-000000000088";
  const projectId = "00000000-0000-4000-8000-000000000099";

  await page.route(/\/v1\/projects(\?|$)/, (route) => {
    if (route.request().method() !== "GET") return route.continue();
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: projectId, name: "Demo" }],
      }),
    });
  });

  await page.route(new RegExp(`/v1/chat/sessions/${sessionId}(/|\\?|$)`), (route) => {
    if (route.request().url().includes("/stream")) return route.continue();
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        session_id: sessionId,
        project_id: projectId,
        my_participant_role: "session_admin",
        participants: [{ user_id: "u1", role: "session_admin", display_name: "Host" }],
        turns: [],
      }),
    });
  });

  await page.route(/\/v1\/compute\/nodes/, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        nodes: [
          {
            node_id: "00000000-0000-4000-8000-000000000001",
            display_name: "alex-mac-e2e",
            status: "online",
            share_policy: "managed_by_host",
            allow_host_resource_management: true,
            capabilities: { claims_total: 4, claims_used: 4 },
          },
        ],
      }),
    }),
  );

  await page.goto(`/v1/maker/app/#/chat?session_id=${sessionId}`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await page.evaluate((sid) => {
    localStorage.setItem("maker_archetype_subchoice", "engineer");
    sessionStorage.setItem("maker_chat_session_id", sid);
  }, sessionId);
  await activateMakerRoute(page, "/chat");
  await expect(page.getByTestId("maker-accessible-compute-trigger")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("maker-accessible-compute-trigger").click({ force: true });
  const drawer = page.getByTestId("maker-accessible-compute");
  await expect(drawer).toBeVisible({ timeout: 15_000 });
  await expect(drawer).toContainText("alex-mac-e2e", { timeout: 15_000 });
  await expect(drawer).toContainText("low headroom", { timeout: 15_000 });
});
