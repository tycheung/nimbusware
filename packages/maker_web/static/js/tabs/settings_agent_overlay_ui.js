import { apiJson, toast } from "../api-client.js";

export function agentOverlaySectionHtml() {
  return `
    <section id="settings-agent-overlays" class="panel" data-testid="maker-settings-agent-overlays">
      <h3>My agent overlays</h3>
      <p class="muted">
        Add prompt text merged when you claim a discipline role in collab sessions.
      </p>
      <label>
        Discipline
        <select id="settings-agent-overlay-discipline" data-testid="maker-settings-agent-overlay-discipline">
          <option value="">— select —</option>
        </select>
      </label>
      <label>
        Prompt extension
        <textarea
          id="settings-agent-overlay-prompt"
          rows="4"
          maxlength="2000"
          placeholder="e.g. Prefer FastAPI idioms and thin handlers."
          data-testid="maker-settings-agent-overlay-prompt"
        ></textarea>
      </label>
      <label>
        Custom agent id (optional)
        <input
          type="text"
          id="settings-agent-overlay-agent-id"
          maxlength="120"
          placeholder="Optional catalog agent id"
          data-testid="maker-settings-agent-overlay-agent-id"
        />
      </label>
      <div class="actions">
        <button
          type="button"
          id="settings-agent-overlay-save"
          class="primary"
          data-testid="maker-settings-agent-overlay-save"
        >
          Save overlay
        </button>
        <button
          type="button"
          id="settings-agent-overlay-clear"
          class="secondary"
          data-testid="maker-settings-agent-overlay-clear"
        >
          Clear overlay
        </button>
      </div>
    </section>`;
}

function overlayRow(overlays, discipline) {
  const row = overlays?.[discipline];
  if (!row || typeof row !== "object") return { prompt_extension: "", custom_agent_id: "" };
  return {
    prompt_extension: String(row.prompt_extension || ""),
    custom_agent_id: String(row.custom_agent_id || ""),
  };
}

export async function wireAgentOverlayPanel(root) {
  const section = root.querySelector("#settings-agent-overlays");
  if (!section) return;

  const select = root.querySelector("#settings-agent-overlay-discipline");
  const promptEl = root.querySelector("#settings-agent-overlay-prompt");
  const agentIdEl = root.querySelector("#settings-agent-overlay-agent-id");
  if (!select || !promptEl || !agentIdEl) return;

  let overlays = {};

  function fillForm(discipline) {
    const row = overlayRow(overlays, discipline);
    promptEl.value = row.prompt_extension;
    agentIdEl.value = row.custom_agent_id;
  }

  async function refresh() {
    try {
      const body = await apiJson("/users/me/agent-overlays");
      overlays = body.overlays || {};
      const disciplines = body.disciplines || [];
      const current = select.value;
      select.replaceChildren();
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— select —";
      select.appendChild(blank);
      for (const d of disciplines) {
        const id = String(d.id || "");
        if (!id) continue;
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = String(d.display_name || id);
        select.appendChild(opt);
      }
      if (current && [...select.options].some((o) => o.value === current)) {
        select.value = current;
      }
      fillForm(select.value);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  select.addEventListener("change", () => fillForm(select.value));

  root.querySelector("#settings-agent-overlay-save")?.addEventListener("click", async () => {
    const discipline = select.value?.trim();
    if (!discipline) return toast("Select a discipline", "error");
    try {
      const body = await apiJson(
        `/users/me/agent-overlays/${encodeURIComponent(discipline)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt_extension: promptEl.value.trim() || null,
            custom_agent_id: agentIdEl.value.trim() || null,
          }),
        },
      );
      overlays = body.overlays || {};
      toast("Agent overlay saved", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  root.querySelector("#settings-agent-overlay-clear")?.addEventListener("click", async () => {
    const discipline = select.value?.trim();
    if (!discipline) return toast("Select a discipline", "error");
    try {
      const body = await apiJson(
        `/users/me/agent-overlays/${encodeURIComponent(discipline)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt_extension: null, custom_agent_id: null }),
        },
      );
      overlays = body.overlays || {};
      promptEl.value = "";
      agentIdEl.value = "";
      toast("Agent overlay cleared", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  await refresh();
}
