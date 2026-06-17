import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("chat run card shows agents strip with model badges", async ({ page }) => {
  const runId = "00000000-0000-4000-8000-000000000099";
  await page.route("**/v1/platform/model-bindings/defaults**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        roles: [
          {
            agent_role: "planner",
            display_name: "Planner",
            binding: {
              provider_id: "ollama",
              provider_kind: "local",
              model_id: "llama3.1:8b",
            },
          },
        ],
      }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/autopilot**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ level: 5, name: "Balanced" }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/theater**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ messages: [], cursor: 0, has_more: false }),
    }),
  );
  await activateMakerRoute(page, "chat");
  await page.goto(`#/chat?run_id=${runId}`);
  const strip = page.getByTestId("maker-chat-agents-strip");
  await expect(strip).toBeVisible();
  await expect(page.getByTestId("maker-chat-agent-planner")).toContainText("llama3.1:8b");
  await expect(page.getByTestId("maker-chat-agent-info-planner")).toBeVisible();
});
