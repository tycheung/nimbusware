import { test, expect } from "@playwright/test";
const RUN_ID = "00000000-0000-4000-8000-000000000005";

test("chat tab shows live theater lines for active run", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );

  let streamHits = 0;
  await page.route(`**/v1/runs/${RUN_ID}/theater/stream`, async (route) => {
    streamHits += 1;
    await route.fulfill({
      contentType: "text/event-stream",
      body:
        'event: theater\ndata: {"actor_display":"Planner","headline":"Planner reviewing scope","body_md":"Scope check"}\n\n' +
        'event: theater\ndata: {"actor_display":"Writer","headline":"Writer applying patch","body_md":"Patch diff"}\n\n',
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await page.evaluate(
    async ({ runId }) => {
      const shell = document.querySelector("[x-data]") as HTMLElement & {
        _x_dataStack?: Array<{ route: string }>;
      };
      const data = shell?._x_dataStack?.[0];
      if (data) data.route = "/chat";
      window.location.hash = `#/chat?run_id=${runId}`;
      const { loadRoute } = await import("/v1/maker/app/js/tab-loader.js");
      await loadRoute("/chat");
    },
    { runId: RUN_ID },
  );

  await expect(page.getByTestId("maker-chat-theater-line").first()).toContainText("Planner", {
    timeout: 10_000,
  });
  await expect(page.locator(".theater-headline").first()).toContainText("Planner:");
  await expect(page.locator("#chat-thread .chat-thread-line--theater").first()).toBeVisible();
  expect(streamHits).toBeGreaterThan(0);
});
