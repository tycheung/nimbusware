import path from "node:path";
import { test, expect, type Page } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";
import { seedCampaign } from "./playwright_seed";

const repoRoot = path.resolve(process.cwd(), "../../..");
const SESSION_ID = "00000000-0000-4000-8000-000000000301";
const SLICE_ID = "api-slice-1";

const ARCHETYPES = [
  { id: "engineer", setupBundle: "default" },
  { id: "safe_coding", setupBundle: "default" },
  { id: "enterprise", setupBundle: "enterprise" },
] as const;

function mockPlatformApis(
  page: Page,
  setupBundle: string,
  projectId: string,
  projectName: string,
) {
  return page.route("**/v1/platform/**", (route) => {
    const url = route.request().url();
    if (url.includes("/fleet-governance")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          setup_bundle: setupBundle,
          mandatory_discovery: setupBundle === "enterprise",
          default_surfaces: ["web", "api"],
          deploy_chain_required: setupBundle === "enterprise",
          allowed_deploy_targets:
            setupBundle === "enterprise"
              ? ["aws-ecs", "aws-static-site", "github-actions"]
              : [],
          enforcement_policy: { min_enforcement_level: 0, max_enforcement_level: 10 },
        }),
      });
    }
    if (url.includes("/readiness")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          status: "ready",
          checks: {},
          setup_bundle: setupBundle,
          edition: setupBundle === "enterprise" ? "enterprise" : "default",
        }),
      });
    }
    if (url.includes("/hardware")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ tier: "mid", ram_available_gb: 16, gpus: [] }),
      });
    }
    if (url.includes("/models/ranked")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ models: [], profile_tier: "mid" }),
      });
    }
    if (url.includes("/onboarding")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ onboarded: true }),
      });
    }
    return route.continue();
  }).then(() =>
    page.route("**/v1/projects**", (route) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projects: [{ project_id: projectId, name: projectName, workspace_path: "/tmp/ws" }],
        }),
      }),
    ),
  );
}

function mockChatDiscovery(page: Page) {
  return page.route("**/v1/chat/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    if (method === "POST" && url.endsWith("/chat/sessions")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ session_id: SESSION_ID, turns: [] }),
      });
    }
    if (method === "GET" && url.includes(SESSION_ID)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          session_id: SESSION_ID,
          turns: [{ turn_id: "t1", role: "user", text: "Build a todo app with web UI and API" }],
        }),
      });
    }
    if (method === "POST" && url.includes("/turns")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          classification: {
            suggested_profile: "campaign_fullstack",
            work_type: "campaign",
            confidence: 0.92,
          },
        }),
      });
    }
    if (method === "POST" && url.includes("/scope/discover")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          scope: {
            discovery_complete: false,
            questions: [
              {
                id: "client_form",
                prompt: "What kind of client do you want?",
                options: ["Web app", "Mobile (web-first)"],
              },
            ],
            answers: [],
          },
        }),
      });
    }
    return route.continue();
  });
}

function mockPlanApis(page: Page, runId: string) {
  return Promise.all([
    page.route(`**/v1/campaigns/${runId}/backlog`, (route) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          epics: [
            {
              title: "Product",
              status: "open",
              features: [
                {
                  title: "API",
                  slices: [
                    {
                      slice_id: SLICE_ID,
                      status: "in_flight",
                      surface_id: "api",
                      stack_id: "fastapi_python",
                    },
                  ],
                },
                {
                  title: "Web",
                  slices: [
                    {
                      slice_id: "web-slice-1",
                      status: "pending",
                      surface_id: "web",
                      stack_id: "react_vite",
                    },
                  ],
                },
              ],
            },
          ],
          summary: { slices_completed: 0, total_slices: 2 },
        }),
      }),
    ),
    page.route(`**/v1/runs/${runId}/timeline**`, (route) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ events: [] }),
      }),
    ),
    page.route(`**/v1/runs/${runId}/maker-progress**`, (route) => {
      if (route.request().url().includes("/stream")) {
        return route.fulfill({ contentType: "text/event-stream", body: "" });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runId,
          status: "building",
          campaign_progress: {
            state: "executing",
            current_slice_id: SLICE_ID,
            slices_completed: 0,
            slices_total: 2,
            next_maintenance: { refactor_in_slices: 5, architecture_in_slices: 10 },
          },
        }),
      });
    }),
  ]);
}

function mockProgressApis(page: Page, runId: string) {
  return Promise.all([
    page.route(`**/v1/runs/${runId}/maker-progress**`, (route) => {
      if (route.request().url().includes("/stream")) {
        return route.fulfill({ contentType: "text/event-stream", body: "" });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runId,
          status: "building",
          current_headline: "Campaign building — slice 1 of 2",
          campaign_progress: { state: "executing", slices_completed: 0, slices_total: 2 },
        }),
      });
    }),
    page.route(`**/v1/runs/${runId}/findings**`, (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ findings: [] }) }),
    ),
    page.route(`**/v1/runs/${runId}/theater/stream**`, (route) =>
      route.fulfill({ contentType: "text/event-stream", body: "" }),
    ),
  ]);
}

for (const arch of ARCHETYPES) {
  test(`${arch.id} product journey: discovery, plan surfaces, deploy cockpit`, async ({ page, request }) => {
    const { projectId, runId } = await seedCampaign(request, repoRoot, `journey-${arch.id}`);
    await page.addInitScript((archetype) => {
      localStorage.setItem("maker_archetype_subchoice", archetype);
    }, arch.id);

    await mockPlatformApis(page, arch.setupBundle, projectId, `journey-${arch.id}`);
    await mockChatDiscovery(page);

    await page.goto("/v1/maker/app/");
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/chat");

    await expect(page.getByTestId("maker-chat-project-select")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("maker-chat-project-select").selectOption(projectId);
    await page.getByTestId("maker-chat-message").fill("Build a todo app with web UI and API");
    await page.getByTestId("maker-chat-start").click();
    await expect(page.getByTestId("maker-chat-discovery-card")).toBeVisible({ timeout: 15_000 });

    await mockPlanApis(page, runId);
    await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/plan`);
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/plan");

    await expect(page.getByTestId("maker-plan-surface-badge").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("maker-plan-current-slice")).toContainText(SLICE_ID);
    await expect(page.getByTestId("maker-plan-maintenance")).toContainText("refactor in");
    await expect(page.locator(".plan-slice--current")).toBeVisible();

    await mockProgressApis(page, runId);
    await page.goto(`/v1/maker/app/?run_id=${encodeURIComponent(runId)}#/progress`);
    await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
    await activateMakerRoute(page, "/progress");
    await expect(page.getByTestId("maker-deploy-cockpit-progress")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("maker-deploy-validate-progress")).toBeVisible();

    if (arch.id === "enterprise") {
      await activateMakerRoute(page, "/home");
      await expect(page.getByTestId("maker-home-enterprise")).toBeVisible({ timeout: 15_000 });
      await expect(page.getByTestId("maker-home-deploy-allowlist")).toContainText("aws-ecs");
    }
  });
}
