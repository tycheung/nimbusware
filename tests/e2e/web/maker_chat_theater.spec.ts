import { test, expect } from "@playwright/test";
const RUN_ID = "00000000-0000-4000-8000-000000000005";

test("chat tab shows live theater lines for active run", async ({ page }) => {
  await page.addInitScript(() => {
    class MockEventSource {
      onmessage: ((ev: MessageEvent) => void) | null = null;
      constructor(_url: string) {
        setTimeout(() => {
          this.onmessage?.({ data: JSON.stringify({ message: "Planner reviewing scope" }) } as MessageEvent);
          this.onmessage?.({ data: JSON.stringify({ message: "Writer applying patch" }) } as MessageEvent);
        }, 30);
      }
      close() {}
    }
    window.EventSource = MockEventSource as typeof EventSource;
  });

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
      body: 'data: {"message":"Planner reviewing scope"}\n\ndata: {"message":"Writer applying patch"}\n\n',
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
});
