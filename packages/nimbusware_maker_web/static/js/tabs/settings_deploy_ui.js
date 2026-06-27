import { toast } from "../api-client.js";

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
        Store connection labels locally until vault-backed deploy credentials ship.
        Secrets belong in Admin → API connections or environment variables.
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
        <button type="submit" class="secondary" data-testid="maker-settings-deploy-save">Save deploy labels</button>
      </form>
      <p id="settings-deploy-hint" class="muted" data-testid="maker-settings-deploy-hint"></p>
    </section>`;
}

export function wireDeploySettingsPanel(root) {
  const form = root.querySelector("#settings-deploy-form");
  if (!form) return;

  const aws = root.querySelector("#settings-deploy-aws");
  const github = root.querySelector("#settings-deploy-github");
  const workflow = root.querySelector("#settings-deploy-workflow");
  const hint = root.querySelector("#settings-deploy-hint");

  const stored = readStored();
  if (aws && stored.aws) aws.value = stored.aws;
  if (github && stored.github) github.value = stored.github;
  if (workflow && stored.workflow) workflow.value = stored.workflow;
  if (hint && (stored.aws || stored.github)) {
    hint.textContent = "Labels saved locally — wire secrets via Admin before live deploy.";
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    writeStored({
      aws: aws?.value?.trim() || "",
      github: github?.value?.trim() || "",
      workflow: workflow?.value?.trim() || "",
    });
    if (hint) hint.textContent = "Deploy connection labels saved.";
    toast("Deploy labels saved", "success");
  });
}
