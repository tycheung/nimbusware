import { test, expect } from "@playwright/test";
import { activateMakerRouteHash } from "./maker_route_helper";

const SESSION_ID = "pw-chat-escalation-session";
const RUN_ID = "00000000-0000-4000-8000-000000000003";
const PROJECT_ID = "00000000-0000-4000-8000-000000000097";

function baseSessionRoutes(page: import("@playwright/test").Page) {
  return page.route("**/v1/chat/sessions**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "GET" && url.includes(SESSION_ID)) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          project_id: PROJECT_ID,
          messages: [{ role: "user", text: "fix test", turn_id: "turn-1" }],
        }),
      });
      return;
    }
    if (url.includes("/graph")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ session_id: SESSION_ID, nodes: [], edges: [], branches: [] }),
      });
      return;
    }
    return route.continue();
  });
}

test("chat offers slice escalation after patch gate fail", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Escalation fixture", workspace_path: "/tmp" }],
      }),
    }),
  );
  await baseSessionRoutes(page);

  await page.route(`**/v1/runs/${RUN_ID}/timeline`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            event_type: "run.created",
            metadata: { work_type: "patch", patch_effective: { enabled: true } },
          },
          {
            event_type: "stage.completed",
            payload: { stage_name: "slice.gate" },
            metadata: { slice_gate_verdict: "FAIL" },
          },
        ],
      }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/theater/stream`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");

  await page.evaluate(
    ({ sid, pid }) => {
      sessionStorage.setItem("maker_chat_session_id", sid);
      sessionStorage.setItem("maker_active_project_id", pid);
      localStorage.setItem("maker_chat_resume_session", "1");
    },
    { sid: SESSION_ID, pid: PROJECT_ID },
  );

  await activateMakerRouteHash(page, `#/chat?run_id=${RUN_ID}`);
  await expect(page.locator("#view-chat")).toBeVisible();
  await expect(page.getByTestId("maker-chat-escalate-slice")).toBeVisible({ timeout: 10_000 });
});

test("chat offers campaign promotion after slice replans", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: PROJECT_ID, name: "Campaign fixture", workspace_path: "/tmp" }],
      }),
    }),
  );
  await baseSessionRoutes(page);

  await page.route(`**/v1/runs/${RUN_ID}/timeline`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          { event_type: "run.created", metadata: { work_type: "slice" } },
          { event_type: "slice.replan", payload: { stage_name: "slice.replan" } },
          { event_type: "slice.replan", payload: { stage_name: "slice.replan" } },
        ],
      }),
    }),
  );

  await page.route(`**/v1/runs/${RUN_ID}/theater/stream`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/turns/turn-1/switch-mode`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        session_id: SESSION_ID,
        project_id: PROJECT_ID,
        work_type_override: "campaign",
        messages: [{ role: "user", text: "fix test", turn_id: "turn-1", kind: "work_type_switch" }],
      }),
    });
  });

  await page.route(`**/v1/chat/sessions/${SESSION_ID}/start`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "00000000-0000-4000-8000-000000000004",
        turn: { role: "run_status", text: "Started campaign run.", turn_id: "turn-2" },
      }),
    });
  });

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");

  await page.evaluate(
    ({ sid, pid }) => {
      sessionStorage.setItem("maker_chat_session_id", sid);
      sessionStorage.setItem("maker_active_project_id", pid);
      localStorage.setItem("maker_chat_resume_session", "1");
    },
    { sid: SESSION_ID, pid: PROJECT_ID },
  );

  await activateMakerRouteHash(page, `#/chat?run_id=${RUN_ID}`);
  await expect(page.getByTestId("maker-chat-escalate-campaign")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("maker-chat-escalate-campaign").click();
  await expect(page).toHaveURL(/run_id=00000000-0000-4000-8000-000000000004/, { timeout: 10_000 });
});
