import { test, expect } from "@playwright/test";
import { activateMakerRoute } from "./maker_route_helper";

test("deploy cockpit refresh polls GitHub workflow CI status", async ({ page }) => {
  const runId = "11111111-1111-1111-1111-111111111111";

  await page.route("**/v1/projects**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ projects: [] }),
    }),
  );
  await page.route("**/v1/platform/readiness**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: "ready", setup_bundle: "enterprise", edition: "enterprise" }),
    }),
  );
  await page.route("**/v1/platform/onboarding**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ onboarded: true }),
    }),
  );
  await page.route("**/v1/platform/deploy/environments**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ default: "dev", environments: ["dev", "staging", "prod"] }),
    }),
  );
  await page.route("**/v1/platform/deploy/credentials**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        github_repo: "acme/todo-app",
        workflow_path: ".github/workflows/nimbusware-ci.yaml",
        deploy_environment: "dev",
      }),
    }),
  );
  await page.route("**/v1/platform/deploy/ci-poll**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "passed",
        detail: "Nimbusware CI · completed · success",
        run_url: "https://github.com/acme/todo-app/actions/runs/42",
      }),
    }),
  );
  await page.route(`**/v1/runs/${runId}/timeline**`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            event_type: "stage.passed",
            payload: { stage_name: "ci.workflow" },
            metadata: { detail: "Nimbusware CI · completed · success" },
          },
        ],
      }),
    }),
  );

  await page.addInitScript((id) => {
    localStorage.setItem("maker_current_run_id", id);
  }, runId);

  await page.goto("/v1/maker/app/");
  await page.waitForFunction(() => typeof (window as Window & { Alpine?: unknown }).Alpine !== "undefined");
  await activateMakerRoute(page, "/progress");

  const ciStatus = page.getByTestId("maker-deploy-ci-status-progress");
  await expect(ciStatus).toContainText("CI: passed", { timeout: 15_000 });
  await expect(ciStatus).toContainText("Nimbusware CI");
});
