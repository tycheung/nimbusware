import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId } from "../session-hub.js";
import { mountSafeCodingReadinessRibbon, mountSafeCodingWizard } from "../safe-coding-wizard.js";
import { isSafeCodingUx } from "../safe-coding-ux.js";
import { renderModelsFirstStrip, renderReadiness } from "./home_readiness_ui.js";

const FACTORY_DEMOS = [
  {
    promptId: "todo_fullstack",
    title: "Todo app",
    prompt: "Build a todo app with a web UI and REST API with tests",
    testId: "maker-factory-demo-todo",
  },
  {
    promptId: "basic_crm_fullstack",
    title: "Basic CRM",
    prompt: "Build a minimal CRM with web UI, authentication, and API",
    testId: "maker-factory-demo-crm",
  },
  {
    promptId: "contacts_fullstack",
    title: "Contacts app",
    prompt: "Build a contacts app with React UI and OpenAPI-backed REST API",
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
    id: "campaign",
    title: "Build an app",
    detail: "Full-stack autonomous delivery from your prompt",
    testId: "maker-intent-campaign",
  },
];

function openChatIntent(intent, extra = {}) {
  const params = new URLSearchParams({ intent });
  if (extra.prompt) params.set("prompt", extra.prompt);
  if (extra.prompt_id) params.set("prompt_id", extra.promptId || extra.prompt_id);
  window.location.hash = `/chat?${params.toString()}`;
}

export async function mountHome(root) {
  root.innerHTML = `<div id="models-first-mount"></div>
    <div id="readiness-mount"></div>
    <div id="safe-coding-ribbon-mount"></div>
    <div id="safe-coding-wizard-mount"></div>
    <section class="maker-safe-coding panel" data-testid="maker-home-safe-coding" id="safe-coding-panel" hidden>
      <h3>Safe Coding</h3>
      <p class="muted">Extra checkpoints and approval before apply — best for non-engineers.</p>
      <a href="#/chat?intent=slice" data-testid="maker-home-safe-coding-link">Start in Chat with Safe Coding preset</a>
      · <a href="https://github.com/nimbusware/nimbusware/blob/main/docs/product/safe-coding.md" target="_blank" rel="noopener">Guide</a>
    </section>
    <section class="maker-intents panel" data-testid="maker-home-intents">
      <h3>What do you want to do?</h3>
      <p class="muted">Pick an intent — Chat maps it to the right workflow (no raw profile names).</p>
      <div class="intent-cards" id="intent-cards"></div>
    </section>
    <section class="guided-campaign panel" data-testid="maker-home-guided-campaign" id="factory-hero-section">
      <h3>Full-stack demos</h3>
      <p class="muted" id="factory-hero-caption">Example product prompts — scope discovery runs in Chat before the campaign starts.</p>
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
    <section class="maker-enterprise panel" data-testid="maker-home-enterprise" id="enterprise-home-panel" hidden>
      <h3>Enterprise operations</h3>
      <p class="muted">Fleet governance, compliance, and audit exports for regulated teams.</p>
      <p class="actions">
        <a href="#/review" data-testid="maker-home-enterprise-review">Review &amp; audit exports</a>
        · <a href="/admin/#/fleet" target="_blank" rel="noopener" data-testid="maker-home-enterprise-fleet">Admin Fleet</a>
        · <a href="/admin/#/fleet?panel=compliance" target="_blank" rel="noopener" data-testid="maker-home-enterprise-compliance">Compliance dashboard</a>
      </p>
    </section>
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
    const safePanel = root.querySelector("#safe-coding-panel");
    const enterprisePanel = root.querySelector("#enterprise-home-panel");
    const factorySection = root.querySelector("#factory-hero-section");
    if (readiness.setup_bundle === "enterprise") {
      if (enterprisePanel) enterprisePanel.hidden = false;
      if (factorySection) factorySection.hidden = true;
      if (safePanel) safePanel.hidden = true;
    } else if (safePanel && readiness.setup_bundle === "default") {
      safePanel.hidden = false;
      if (isSafeCodingUx()) {
        await mountSafeCodingWizard(root);
        await mountSafeCodingReadinessRibbon(root);
      }
    }
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
  let factoryWeekly = null;
  try {
    const summary = await apiJson("/platform/analytics/competitive-summary");
    factoryWeekly = summary?.metrics?.factory_weekly || summary?.factory_weekly || null;
    const caption = root.querySelector("#factory-hero-caption");
    if (caption && factoryWeekly?.pass_rate != null) {
      const pct = Math.round(Number(factoryWeekly.pass_rate) * 100);
      const when = factoryWeekly.published_at ? ` (${String(factoryWeekly.published_at).slice(0, 10)})` : "";
      caption.textContent = `Weekly factory soak: ${pct}% pass rate${when}. Pick a catalog demo or start a custom prompt.`;
    }
  } catch {
    /* metrics optional when store empty */
  }

  const catalogIds = new Set(
    Array.isArray(factoryWeekly?.prompt_ids) ? factoryWeekly.prompt_ids.map(String) : [],
  );
  for (const demo of FACTORY_DEMOS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "intent-card";
    btn.dataset.testid = demo.testId;
    const inCatalog = catalogIds.has(demo.promptId);
    const catalogNote =
      factoryWeekly?.pass_rate != null && inCatalog
        ? ` · catalog ${Math.round(Number(factoryWeekly.pass_rate) * 100)}% weekly`
        : "";
    btn.innerHTML = `<strong>${demo.title}</strong><span class="muted">${demo.prompt}${catalogNote}</span>`;
    btn.addEventListener("click", () =>
      openChatIntent("campaign", { prompt: demo.prompt, promptId: demo.promptId }),
    );
    factoryCards?.appendChild(btn);
  }

  root.querySelector("#home-start-factory")?.addEventListener("click", () => {
    openChatIntent("campaign");
  });

  await refresh();
}
