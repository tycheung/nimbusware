import path from "node:path";
import { test, expect } from "@playwright/test";
import { activateMakerRoute, activateMakerRouteHash } from "./maker_route_helper";
import { adminToken, seedCampaign, seedProjectAndRun } from "./playwright_seed";

const repoRoot = path.resolve(process.cwd(), "../../..");
const SESSION_ID = "pw-ext-escalation-session";
const ESC_RUN_ID = "00000000-0000-4000-8000-000000000020";
const ESC_PROJECT_ID = "00000000-0000-4000-8000-000000000098";

test("campaign pause posts pause action", async ({ page, request }) => {
  const { runId } = await seedCampaign(request, repoRoot, "pause-click");
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-campaign-pause")).toBeVisible({ timeout: 15_000 });
  const pausePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/campaigns/${runId}/pause`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-campaign-pause").click();
  expect((await pausePromise).ok()).toBeTruthy();
});

test("build tab starts campaign from form submit", async ({ page, request }) => {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-build-${Date.now()}`,
      workspace_path: `${repoRoot}/tests/fixtures/repos/tiny_python_app`.replace(/\\/g, "/"),
      template: "attach",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id as string;

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRouteHash(page, "#/build?campaign=1");

  await expect(page.getByTestId("maker-build-start-run")).toBeVisible({ timeout: 15_000 });
  await page.locator("#build-project-select").selectOption(projectId);
  await page.locator("#intent-form textarea[name='prompt']").fill("Build tab campaign from Playwright");
  const startPromise = page.waitForResponse(
    (resp) => resp.url().includes("/v1/campaigns") && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-build-start-run").click();
  expect((await startPromise).ok()).toBeTruthy();
  await expect(page).toHaveURL(/#\/progress\?run_id=/);
});

test("wizard quick demo navigates to chat", async ({ page }) => {
  await page.route("**/v1/platform/onboarding", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ onboarded: false }),
    }),
  );
  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/home");

  await expect(page.getByTestId("maker-guided-start-quick")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("maker-guided-start-quick").click();
  await expect(page).toHaveURL(/#\/chat/);
});

test("review approve plan posts approve endpoint", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "approve-plan");
  await page.route(`**/v1/runs/${runId}/maker/pending`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ plan_approved: false, awaiting_approval: false }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/maker/git-status`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({}) }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");

  await expect(page.getByTestId("maker-review-refresh")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("maker-review-refresh").click();
  await expect(page.getByTestId("maker-review-approve-plan")).toBeVisible({ timeout: 10_000 });

  const approvePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/maker/plan/approve`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-review-approve-plan").click();
  expect((await approvePromise).ok()).toBeTruthy();
});

test("review run launch check posts launch-eval", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "review-launch-eval");
  await page.route(`**/v1/runs/${runId}/maker/pending`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({}) }),
  );
  await page.route(`**/v1/runs/${runId}/maker/git-status`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({}) }),
  );
  await page.route(`**/v1/runs/${runId}/timeline**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            event_type: "launch_eval.completed",
            payload: { aggregate: 0.8, maturity: "beta" },
          },
        ],
      }),
    }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");

  await expect(page.getByTestId("maker-review-run-launch-eval")).toBeVisible({ timeout: 15_000 });
  const launchPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/maker/launch-eval`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-review-run-launch-eval").click();
  expect((await launchPromise).ok()).toBeTruthy();
});

test("review factory evidence load renders scorecard rows", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "factory-evidence");
  await page.route(`**/v1/runs/${runId}/maker/pending`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({}) }),
  );
  await page.route(`**/v1/runs/${runId}/maker/git-status`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({}) }),
  );
  await page.route(`**/v1/runs/${runId}/factory-evidence`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        scorecard_rows: [{ dimension: "security", score: 0.9, notes: "ok" }],
      }),
    }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/review`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/review");

  await expect(page.getByTestId("maker-review-factory-evidence-load")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("maker-review-factory-evidence-load").click();
  await expect(page.locator("#rev-factory-evidence-rows")).toContainText("security");
});

test("chat escalate slice switches work type", async ({ page }) => {
  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projects: [{ project_id: ESC_PROJECT_ID, name: "Slice escalation", workspace_path: "/tmp" }],
      }),
    }),
  );
  await page.route("**/v1/chat/sessions**", async (route) => {
    const url = route.request().url();
    if (route.request().method() === "GET" && url.includes(SESSION_ID)) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          project_id: ESC_PROJECT_ID,
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
  await page.route(`**/v1/runs/${ESC_RUN_ID}/timeline`, (route) =>
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
  await page.route(`**/v1/runs/${ESC_RUN_ID}/theater/stream`, (route) =>
    route.fulfill({ contentType: "text/event-stream", body: "" }),
  );
  await page.route(`**/v1/chat/sessions/${SESSION_ID}/turns/turn-1/switch-mode`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        session_id: SESSION_ID,
        project_id: ESC_PROJECT_ID,
        work_type_override: "slice",
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
    { sid: SESSION_ID, pid: ESC_PROJECT_ID },
  );
  await activateMakerRouteHash(page, `#/chat?run_id=${ESC_RUN_ID}`);

  await expect(page.getByTestId("maker-chat-escalate-slice")).toBeVisible({ timeout: 10_000 });
  const switchPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/chat/sessions/${SESSION_ID}/turns/turn-1/switch-mode`) &&
      resp.request().method() === "POST",
  );
  await page.getByTestId("maker-chat-escalate-slice").click();
  expect((await switchPromise).ok()).toBeTruthy();
});

test("dev env stop posts stop endpoint", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "dev-env-stop");
  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-dev-env-stop")).toBeVisible({ timeout: 15_000 });
  const stopPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/dev-env/stop`) && resp.request().method() === "POST",
  );
  await page.getByTestId("maker-dev-env-stop").click();
  expect((await stopPromise).ok()).toBeTruthy();
});

test("integrator promote batch posts promote endpoint", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "integrator-promote");
  await page.route("**/v1/bundles/catalog-candidates**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ candidates: [{ status: "pending", id: "c1" }] }),
    }),
  );
  await page.route("**/v1/bundles/catalog**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ document_version: 1 }),
    }),
  );
  await page.route("**/v1/bundles/catalog-candidates/promote-stitch-pending**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ promoted: 1 }),
    }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-integrator-stitch-promote-batch")).toBeVisible({ timeout: 15_000 });
  const promotePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes("/v1/bundles/catalog-candidates/promote-stitch-pending") &&
      resp.request().method() === "POST",
  );
  await page.getByTestId("maker-integrator-stitch-promote-batch").click();
  expect((await promotePromise).ok()).toBeTruthy();
});

test("compact save artifact posts from-compaction", async ({ page, request }) => {
  const { projectId, runId } = await seedProjectAndRun(request, repoRoot, "compact-save");
  await page.route(`**/v1/runs/${runId}/context-artifacts/from-compaction`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ artifact_id: "art-1", title: "Compaction snapshot" }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/timeline**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            event_type: "run.created",
            metadata: { project: { id: projectId } },
          },
        ],
      }),
    }),
  );
  await page.route(`**/v1/projects/${projectId}/context-artifacts**`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ artifacts: [] }) }),
  );

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-compact-save-artifact")).toBeVisible({ timeout: 15_000 });
  const savePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/v1/runs/${runId}/context-artifacts/from-compaction`) &&
      resp.request().method() === "POST",
  );
  await page.getByTestId("maker-compact-save-artifact").click();
  expect((await savePromise).ok()).toBeTruthy();
});

test("plan refresh reloads campaign backlog", async ({ page, request }) => {
  const { runId } = await seedCampaign(request, repoRoot, "plan-refresh");
  let backlogCalls = 0;
  await page.route(`**/v1/campaigns/${runId}/backlog`, (route) => {
    backlogCalls += 1;
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        epics: [
          {
            title: "Epic A",
            status: "open",
            features: [{ title: "Feature 1", slices: [{ slice_id: "s1", status: "pending" }] }],
          },
        ],
        summary: { slices_completed: 0, total_slices: 1 },
      }),
    });
  });

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/plan`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/plan");

  await expect(page.getByTestId("maker-plan-refresh")).toBeVisible({ timeout: 15_000 });
  const before = backlogCalls;
  await page.getByTestId("maker-plan-refresh").click();
  await expect(page.getByTestId("maker-plan-tree")).toBeVisible();
  expect(backlogCalls).toBeGreaterThan(before);
});

test("autopilot profile save posts user profile", async ({ page, request }) => {
  const { runId } = await seedProjectAndRun(request, repoRoot, "autopilot-profile");
  page.on("dialog", async (dialog) => {
    if (dialog.type() !== "prompt") {
      await dialog.dismiss();
      return;
    }
    const msg = dialog.message().toLowerCase();
    await dialog.accept(msg.includes("slug") || msg.includes("profile id") ? "pw-profile" : "PW Profile");
  });

  await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  await expect(page.getByTestId("maker-autopilot-profile-save")).toBeVisible({ timeout: 15_000 });
  const savePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes("/v1/platform/autopilot/user-profiles/pw-profile") &&
      resp.request().method() === "PUT",
  );
  await page.getByTestId("maker-autopilot-profile-save").click();
  expect((await savePromise).ok()).toBeTruthy();
});
