import { expect, type APIRequestContext } from "@playwright/test";

export const adminToken =
  process.env.NIMBUSWARE_ADMIN_TOKEN || "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD";

export function fixtureWorkspace(repoRoot: string): string {
  return `${repoRoot}/tests/fixtures/repos/tiny_python_app`.replace(/\\/g, "/");
}

export async function seedProjectAndRun(
  request: APIRequestContext,
  repoRoot: string,
  label: string,
  workflowProfile = "micro_slice",
): Promise<{ projectId: string; runId: string }> {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-${label}-${Date.now()}`,
      workspace_path: fixtureWorkspace(repoRoot),
      template: "attach",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id as string;
  const runResp = await request.post("/v1/runs", {
    data: {
      workflow_profile: workflowProfile,
      project_id: projectId,
      requirements: { business_prompt: label },
    },
  });
  expect(runResp.ok()).toBeTruthy();
  return { projectId, runId: (await runResp.json()).run_id as string };
}

export async function seedCampaign(
  request: APIRequestContext,
  repoRoot: string,
  label: string,
): Promise<{ projectId: string; runId: string }> {
  const headers = { "X-Nimbusware-Admin-Token": adminToken };
  const project = await request.post("/v1/projects", {
    headers,
    data: {
      name: `pw-camp-${label}-${Date.now()}`,
      workspace_path: fixtureWorkspace(repoRoot),
      template: "attach",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id as string;
  const campaign = await request.post("/v1/campaigns", {
    headers,
    data: {
      project_id: projectId,
      requirements: { business_prompt: label },
      autonomous: true,
      workflow_profile: "campaign_micro_slice",
    },
  });
  expect(campaign.ok()).toBeTruthy();
  return { projectId, runId: (await campaign.json()).run_id as string };
}
