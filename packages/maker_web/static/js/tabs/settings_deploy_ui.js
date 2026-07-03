import { apiJson, toast } from "../api-client.js";

const STORAGE_KEY = "maker_deploy_connections";

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeStored(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function deploySettingsSectionHtml() {
  return `
    <section id="settings-deploy" class="panel" data-testid="maker-settings-deploy">
      <h3>Deploy connections</h3>
      <p class="muted">
        Connection labels are stored per user (no secrets). Wire AWS/GitHub secrets via Admin or environment variables.
      </p>
      <form id="settings-deploy-form">
        <label>
          AWS profile / role label
          <input type="text" id="settings-deploy-aws" data-testid="maker-settings-deploy-aws"
            placeholder="e.g. staging-deploy-role" autocomplete="off" />
        </label>
        <label>
          GitHub org / repo
          <input type="text" id="settings-deploy-github" data-testid="maker-settings-deploy-github"
            placeholder="org/repo" autocomplete="off" />
        </label>
        <label>
          Default CI workflow
          <input type="text" id="settings-deploy-workflow" data-testid="maker-settings-deploy-workflow"
            placeholder=".github/workflows/deploy.yml" autocomplete="off" />
        </label>
        <label>
          Default deploy environment
          <select id="settings-deploy-environment" data-testid="maker-settings-deploy-environment">
            <option value="dev">dev</option>
            <option value="staging">staging</option>
            <option value="prod">prod</option>
          </select>
        </label>
        <button type="submit" class="secondary" data-testid="maker-settings-deploy-save">Save deploy labels</button>
      </form>
      <p id="settings-deploy-hint" class="muted" data-testid="maker-settings-deploy-hint"></p>
    </section>`;
}

export async function wireDeploySettingsPanel(root) {
  const form = root.querySelector("#settings-deploy-form");
  if (!form) return;

  const aws = root.querySelector("#settings-deploy-aws");
  const github = root.querySelector("#settings-deploy-github");
  const workflow = root.querySelector("#settings-deploy-workflow");
  const environment = root.querySelector("#settings-deploy-environment");
  const hint = root.querySelector("#settings-deploy-hint");

  let stored = readStored();
  try {
    const remote = await apiJson("/platform/deploy/credentials");
    stored = { ...stored, ...remote };
  } catch {
    /* offline or unsigned */
  }
  if (aws && stored.aws_profile) aws.value = stored.aws_profile;
  else if (aws && stored.aws) aws.value = stored.aws;
  if (github && stored.github_repo) github.value = stored.github_repo;
  else if (github && stored.github) github.value = stored.github;
  if (workflow && stored.workflow_path) workflow.value = stored.workflow_path;
  else if (workflow && stored.workflow) workflow.value = stored.workflow;
  if (environment && stored.deploy_environment) environment.value = stored.deploy_environment;
  if (hint && (stored.aws_profile || stored.aws || stored.github_repo || stored.github)) {
    hint.textContent = "Labels saved — copy GitHub workflow from Deploy cockpit or GET /platform/deploy/github-workflow-template.";
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const payload = {
      aws: aws?.value?.trim() || "",
      github: github?.value?.trim() || "",
      workflow: workflow?.value?.trim() || "",
      deploy_environment: environment?.value || "dev",
    };
    writeStored(payload);
    try {
      await apiJson("/platform/deploy/credentials", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          aws_profile: payload.aws,
          github_repo: payload.github,
          workflow_path: payload.workflow,
          deploy_environment: payload.deploy_environment,
        }),
      });
    } catch {
      /* local-only fallback */
    }
    if (hint) hint.textContent = "Deploy connection labels saved.";
    toast("Deploy labels saved", "success");
  });
}
