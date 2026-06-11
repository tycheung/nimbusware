import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId } from "../session-hub.js";

const GUIDED_STEPS = [
  { id: "quick", label: "Try quick demo (no Postgres)", hash: "/chat" },
  { id: "readiness", label: "Check platform readiness", hash: "/home" },
  { id: "project", label: "Create or select a project", hash: "/home" },
  { id: "models", label: "Pick a model preset", hash: "/models" },
  { id: "campaign", label: "Start an autonomous campaign", hash: "/build?campaign=1" },
  { id: "plan", label: "Review the delivery backlog", hash: "/plan" },
  { id: "progress", label: "Watch progress theater", hash: "/progress" },
];

export async function mountWizard(root) {
  const state = await apiJson("/platform/onboarding");
  if (state.onboarded) {
    root.innerHTML = "<p>Setup complete. Use Home to manage projects.</p>";
    return;
  }
  root.innerHTML = `
    <section class="guided-campaign" data-testid="maker-guided-campaign">
      <h3>First-run setup</h3>
      <p class="muted" data-testid="maker-guided-quick-hint">
        New here? Run <code>poetry run nimbusware-run --quick</code> in a terminal for an in-memory
        demo (stub critics, no Postgres), then open Chat below.
      </p>
      <ol id="guided-checklist" class="guided-checklist"></ol>
      <div class="actions">
        <button type="button" id="wizard-start-quick" class="primary" data-testid="maker-guided-start-quick">Open Chat (quick demo)</button>
        <button type="button" id="wizard-start-campaign" data-testid="maker-guided-start-campaign">Start guided campaign</button>
        <button type="button" id="wizard-start-build">Quick build (non-campaign)</button>
        <button type="button" id="wizard-done" class="secondary">Mark setup complete</button>
      </div>
    </section>`;

  const list = root.querySelector("#guided-checklist");
  for (const step of GUIDED_STEPS) {
    const li = document.createElement("li");
    li.dataset.testid = `maker-guided-step-${step.id}`;
    const link = document.createElement("a");
    link.href = `#${step.hash}`;
    link.textContent = step.label;
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      window.location.hash = step.hash;
    });
    li.appendChild(link);
    list?.appendChild(li);
  }

  root.querySelector("#wizard-start-quick")?.addEventListener("click", () => {
    window.location.hash = "/chat";
    toast("Use Chat with --quick running, or attach tests/fixtures/repos/tiny_python_app", "info");
  });
  root.querySelector("#wizard-start-campaign")?.addEventListener("click", () => {
    const sel = document.querySelector("#build-project-select");
    const projectId = sel?.value || sessionStorage.getItem("maker_active_project_id");
    if (projectId) setActiveProjectId(String(projectId));
    window.location.hash = "/build?campaign=1";
    toast("Campaign mode selected — enter a prompt and start", "info");
  });
  root.querySelector("#wizard-start-build")?.addEventListener("click", () => {
    window.location.hash = "/build";
  });
  root.querySelector("#wizard-done")?.addEventListener("click", async () => {
    await apiJson("/platform/onboarding", { method: "POST" });
    toast("Onboarding complete", "success");
    window.location.hash = "/home";
  });
}
