import { apiJson, toast } from "../api-client.js";

export function readinessAction(check) {
  const action = check?.action;
  if (!action) return null;
  switch (action) {
    case "quick_mode":
      return () => {
        window.location.hash = "/settings";
        toast("Enable quick mode under Settings, or run: poetry run nimbusware-run --quick", "info");
      };
    case "start_ollama":
      return () => {
        window.location.hash = "/models?section=local";
      };
    case "pull_model":
      return () => {
        window.location.hash = "/models?section=local";
      };
    case "model_hub_local":
      return () => {
        window.location.hash = "/models?section=local";
      };
    case "model_hub_api":
      return () => {
        window.location.hash = "/models?section=api-connections";
      };
    case "setup_llm":
      return () => {
        window.location.hash = "/models?section=local";
      };
    case "install_guide":
      return () => toast("See README Quick start and scripts/install_nimbusware.py", "info");
    default:
      return null;
  }
}

export function renderReadiness(mount, readiness) {
  if (!mount) return;
  const status = readiness.status || "unknown";
  mount.replaceChildren();
  const head = document.createElement("section");
  head.className = "panel readiness-panel";
  head.dataset.testid = "maker-home-readiness";
  const title = document.createElement("h3");
  title.textContent = "System readiness";
  head.appendChild(title);
  const summary = document.createElement("p");
  summary.dataset.testid = "maker-home-readiness-status";
  summary.textContent = `Overall: ${status}`;
  head.appendChild(summary);
  const list = document.createElement("ul");
  list.className = "readiness-check-list";
  for (const [key, check] of Object.entries(readiness.checks || {})) {
    const li = document.createElement("li");
    li.className = `readiness-check readiness-check--${check.status || "unknown"}`;
    li.dataset.testid = `maker-readiness-${key}`;
    const label = document.createElement("span");
    label.textContent = `${key}: ${check.message || check.status}`;
    li.appendChild(label);
    const handler = readinessAction(check);
    if (handler && check.action_label) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "linkish";
      btn.textContent = check.action_label;
      btn.dataset.testid = `maker-readiness-action-${key}`;
      btn.addEventListener("click", handler);
      li.appendChild(btn);
    }
    list.appendChild(li);
  }
  head.appendChild(list);
  if (readiness.inference_mode_label) {
    const mode = document.createElement("p");
    mode.className = "muted";
    mode.dataset.testid = "maker-home-inference-mode";
    mode.textContent = readiness.inference_mode_label;
    head.appendChild(mode);
  }
  if (readiness.install_profile) {
    const profile = document.createElement("p");
    profile.className = "muted";
    profile.dataset.testid = "maker-home-install-profile";
    profile.textContent = `Install profile: ${readiness.install_profile}`;
    head.appendChild(profile);
  }
  if (readiness.model_hub_cta) {
    const cta = document.createElement("button");
    cta.type = "button";
    cta.className = "secondary";
    cta.dataset.testid = "maker-home-model-hub-cta";
    cta.textContent = readiness.model_hub_cta;
    cta.addEventListener("click", () => {
      const action = readiness.model_hub_action || "setup_llm";
      const handler = readinessAction({ action });
      handler?.();
    });
    head.appendChild(cta);
  }
  mount.appendChild(head);
}

export async function renderModelsFirstStrip(mount) {
  if (!mount) return;
  try {
    const [hardware, ranked] = await Promise.all([
      apiJson("/platform/hardware"),
      apiJson("/platform/models/ranked?limit=5"),
    ]);
    const top = (ranked.models || [])[0];
    const tier = hardware.tier || ranked.profile_tier || "unknown";
    const ram =
      hardware.ram_available_gb != null ? `${hardware.ram_available_gb} GB free` : "RAM n/a";
    const gpuCount = Array.isArray(hardware.gpus) ? hardware.gpus.length : 0;
    mount.replaceChildren();
    const panel = document.createElement("section");
    panel.className = "panel models-first-strip";
    panel.dataset.testid = "maker-home-models-first";
    const title = document.createElement("h3");
    title.textContent = "Your machine";
    panel.appendChild(title);
    const summary = document.createElement("p");
    summary.className = "muted";
    summary.textContent = `Hardware tier ${tier} · ${ram} · ${gpuCount} GPU(s) detected`;
    panel.appendChild(summary);
    if (top?.model_id) {
      const pick = document.createElement("p");
      pick.dataset.testid = "maker-home-model-pick";
      pick.textContent = `Recommended model: ${top.model_id} (${top.fit_level || "fit unknown"})`;
      panel.appendChild(pick);
      const actions = document.createElement("div");
      actions.className = "actions";
      const modelsBtn = document.createElement("button");
      modelsBtn.type = "button";
      modelsBtn.className = "secondary";
      modelsBtn.textContent = "Apply preset on Models tab";
      modelsBtn.dataset.testid = "maker-home-models-wizard";
      modelsBtn.addEventListener("click", () => {
        window.location.hash = "/models";
      });
      actions.appendChild(modelsBtn);
      panel.appendChild(actions);
    }
    mount.appendChild(panel);
  } catch {
    mount.replaceChildren();
  }
}
