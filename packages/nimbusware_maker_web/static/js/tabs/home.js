import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId } from "../session-hub.js";

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
      return () => toast("Start Ollama (ollama serve), then refresh Home", "info");
    case "pull_model":
      return () => {
        const cmd = check.pull_command || "ollama pull <model>";
        toast(`Run in a terminal: ${cmd}`, "info");
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
  mount.appendChild(head);
}

function openChatIntent(intent) {
  window.location.hash = `/chat?intent=${encodeURIComponent(intent)}`;
}

export async function mountHome(root) {
  root.innerHTML = `<div id="readiness-mount"></div>
    <section class="maker-intents panel" data-testid="maker-home-intents">
      <h3>What do you want to do?</h3>
      <p class="muted">Pick an intent — Chat maps it to the right workflow (no raw profile names).</p>
      <div class="intent-cards" id="intent-cards"></div>
    </section>
    <section class="guided-campaign panel" data-testid="maker-home-guided-campaign">
      <h3>Factory hero demos</h3>
      <p class="muted">Catalog apps: todo API, basic CRM, contacts API — zero-touch factory profile.</p>
      <button type="button" id="home-start-factory" class="primary" data-testid="maker-home-start-factory">Build an app (factory)</button>
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

  root.querySelector("#home-start-factory")?.addEventListener("click", () => {
    openChatIntent("factory");
  });

  await refresh();
}
