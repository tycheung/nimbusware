import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

const RUN_ID = "00000000-0000-4000-8000-000000000010";

test("progress blocking findings show interject and widen in chat actions", async ({ page }) => {
  await page.route(`**/v1/runs/${RUN_ID}/maker-progress**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: RUN_ID,
        verdict: "blocked",
        gate_summary: { blocked: true, headline: "Gate failed" },
        blocking_findings: [{ severity: "BLOCKER", summary: "Tests failed" }],
      }),
    }),
  );
  await page.route(`**/v1/runs/${RUN_ID}/findings**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        findings: [
          {
            event_type: "finding.emitted",
            payload: { severity: "BLOCKER", summary: "Slice gate failed", category: "gate" },
          },
        ],
      }),
    }),
  );
  await page.route(`**/v1/runs/${RUN_ID}/theater/stream**`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );
  await page.route(`**/v1/runs/${RUN_ID}/maker-progress/stream**`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(RUN_ID)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-finding-action-interject")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("maker-finding-action-widen")).toBeVisible();

  await page.getByTestId("maker-finding-action-widen").click();
  await expect(page).toHaveURL(/#\/chat\?intent=slice/);
});
