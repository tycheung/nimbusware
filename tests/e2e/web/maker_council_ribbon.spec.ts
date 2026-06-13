import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const RUN_ID = "00000000-0000-4000-8000-000000000007";

test("progress council ribbon shows improvement gaps from timeline", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/maker-progress**`, (route) => {
    if (route.request().url().includes("/stream")) return route.abort();
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID, stages: [], percent_complete: 0 }),
    });
  });

  await page.route(`**/v1/runs/${RUN_ID}/timeline**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            event_type: "improvement.council",
            metadata: {
              improvement_council: {
                selected: "implement_planned",
                feature_gap_matrix: {
                  gaps: ["auth_flow", "billing_ui"],
                  backlog_ready: 2,
                },
              },
            },
          },
        ],
      }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/memory-influence`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ run_id: RUN_ID, rows: [] }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/theater/stream`, (route) => route.abort());

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(RUN_ID)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const ribbon = page.getByTestId("maker-council-ribbon");
  await expect(ribbon).toBeVisible({ timeout: 10_000 });
  await expect(page.locator("#council-body")).toContainText("Improvement: implement_planned");
  await expect(page.locator("#council-body")).toContainText("Gaps: auth_flow, billing_ui");
});
