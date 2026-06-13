import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const RUN_ID = "00000000-0000-4000-8000-000000000006";

function progressRunMocks(runId: string) {
  return {
    makerProgress: {
      run_id: runId,
      stages: [],
      percent_complete: 0,
    },
  };
}

test("progress tab renders memory influence rows", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/memory-influence`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: RUN_ID,
        rows: [
          { stage: "slice.plan", hits: 3, query_digest: "abc123" },
          { stage: "slice.apply", hits: 1, query_digest: "def456" },
        ],
      }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/maker-progress**`, (route) => {
    if (route.request().url().includes("/stream")) return route.abort();
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(progressRunMocks(RUN_ID).makerProgress),
    });
  });

  await page.route(`**/v1/runs/${RUN_ID}/timeline**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ events: [] }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/theater/stream`, (route) => route.abort());

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(RUN_ID)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const table = page.getByTestId("maker-memory-influence-table");
  await expect(table).toBeVisible({ timeout: 10_000 });
  const rows = page.getByTestId("maker-memory-influence-row");
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText("slice.plan");
  await expect(rows.first()).toContainText("abc123");
});
