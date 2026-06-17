import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId } from "../session-hub.js";

const FACTORY_DEMOS = [
  {
    promptId: "todo_api",
    title: "Todo API",
    prompt: "Build a minimal todo list REST API with tests",
    testId: "maker-factory-demo-todo",
  },
  {
    promptId: "basic_crm",
    title: "Basic CRM",
    prompt: "Build a minimal CRM with user authentication",
    testId: "maker-factory-demo-crm",
  },
  {
    promptId: "contacts_api",
    title: "Contacts API",
    prompt: "Build a contacts REST API with OpenAPI docs",
    testId: "maker-factory-demo-contacts",
  },
];

const INTENT_CARDS = [
  {
    id: "patch",
    title: "Fix a bug",
    detail: "Scoped patch with failing test context",
    testId: "maker-intent-patch",
  },
  {
    id: "slice",
    title: "Build a feature",
    detail: "Micro-slice plan with gates and tests",
    testId: "maker-intent-slice",
  },
  {
    id: "factory",
    title: "Build an app",
    detail: "Autonomous factory from a business prompt",
    testId: "maker-intent-factory",
  },
];

function readinessAction(check) {
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

function renderReadiness(mount, readiness) {
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

function openChatIntent(intent, extra = {}) {
  const params = new URLSearchParams({ intent });
  if (extra.prompt) params.set("prompt", extra.prompt);
  if (extra.prompt_id) params.set("prompt_id", extra.promptId || extra.prompt_id);
  window.location.hash = `/chat?${params.toString()}`;
}

async function renderModelsFirstStrip(mount) {
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

export async function mountHome(root) {
  root.innerHTML = `<div id="models-first-mount"></div>
    <div id="readiness-mount"></div>
    <section class="maker-intents panel" data-testid="maker-home-intents">
      <h3>What do you want to do?</h3>
      <p class="muted">Pick an intent — Chat maps it to the right workflow (no raw profile names).</p>
      <div class="intent-cards" id="intent-cards"></div>
    </section>
    <section class="guided-campaign panel" data-testid="maker-home-guided-campaign">
      <h3>Factory hero demos</h3>
      <p class="muted">Catalog zero-touch factory prompts — weekly pass rates appear in Admin Metrics.</p>
      <div class="intent-cards" id="factory-demo-cards"></div>
      <button type="button" id="home-start-factory" class="secondary" data-testid="maker-home-start-factory">Custom app prompt…</button>
      <p class="actions">
        <a href="#/wizard" data-testid="maker-home-guided-wizard-link">First campaign? Open guided wizard</a>
      </p>
    </section>
    <h3>Projects</h3>
    <ul id="project-list"></ul>
    <form id="project-form">
      <label>Name <input name="name" required /></label>
      <label>Workspace path <input name="workspace_path" required /></label>
      <button type="submit" class="primary">Create project</button>
    </form>
    <p class="muted">To delete a project, use the Admin console (requires admin token).</p>`;

  const cards = root.querySelector("#intent-cards");
  for (const card of INTENT_CARDS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "intent-card";
    btn.dataset.testid = card.testId;
    btn.innerHTML = `<strong>${card.title}</strong><span class="muted">${card.detail}</span>`;
    btn.addEventListener("click", () => openChatIntent(card.id));
    cards?.appendChild(btn);
  }

  await renderModelsFirstStrip(root.querySelector("#models-first-mount"));

  try {
    const readiness = await apiJson("/platform/readiness");
    renderReadiness(root.querySelector("#readiness-mount"), readiness);
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  async function refresh() {
    const listing = await apiJson("/projects");
    const list = root.querySelector("#project-list");
    if (!list) return;
    list.replaceChildren();
    for (const p of listing.projects || []) {
      const li = document.createElement("li");
      li.textContent = `${p.name || p.project_id} — ${p.workspace_path || ""}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Select";
      btn.onclick = () => {
        setActiveProjectId(String(p.project_id));
        toast(`Project ${p.name} selected`);
      };
      li.appendChild(btn);
      list.appendChild(li);
    }
  }

  root.querySelector("#project-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    await apiJson("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: fd.get("name"),
        workspace_path: fd.get("workspace_path"),
      }),
    });
    toast("Project created", "success");
    await refresh();
  });

  const factoryCards = root.querySelector("#factory-demo-cards");
  for (const demo of FACTORY_DEMOS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "intent-card";
    btn.dataset.testid = demo.testId;
    btn.innerHTML = `<strong>${demo.title}</strong><span class="muted">${demo.prompt}</span>`;
    btn.addEventListener("click", () =>
      openChatIntent("factory", { prompt: demo.prompt, promptId: demo.promptId }),
    );
    factoryCards?.appendChild(btn);
  }

  root.querySelector("#home-start-factory")?.addEventListener("click", () => {
    openChatIntent("factory");
  });

  await refresh();
}
