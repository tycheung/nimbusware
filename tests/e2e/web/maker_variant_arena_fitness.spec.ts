import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const RUN_ID = "00000000-0000-4000-8000-000000000008";

test("progress variant ribbon lists candidate fitness rows", async ({ page }) => {
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
            event_type: "variant.arena",
            metadata: {
              variant_arena: {
                candidates: [
                  { id: "a", label: "baseline", fitness: 0.72 },
                  { id: "b", label: "refactor", fitness: 0.81 },
                ],
                winner: { label: "crossover_baseline+refactor", fitness: 0.95 },
                crossover_merged: true,
                crossover_paths: ["a.py", "b.py"],
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

  await expect(page.getByTestId("maker-variant-ribbon")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("maker-variant-body")).toContainText("2 candidate(s)");
  await expect(page.getByTestId("maker-variant-body")).toContainText("crossover_baseline+refactor");
  await expect(page.getByTestId("maker-variant-body")).toContainText("crossover merged");
  await expect(page.getByTestId("maker-variant-body")).toContainText("crossover: a.py, b.py");
  const rows = page.getByTestId("maker-variant-candidate");
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText("baseline: fitness 0.72");
  await expect(rows.nth(1)).toContainText("refactor: fitness 0.81");
});
