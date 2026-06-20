import { apiJson, toast } from "../api-client.js";
import { renderCriticReliabilityPanel, loadRunOrFleetCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard } from "../launch-scorecard.js";
import { getActiveProjectId, hydrateActiveRun, resolveRunId } from "../session-hub.js";

const GOVERNOR_KEYS = new Set([
  "NIMBUSWARE_MAX_SYSTEM_RAM_PCT",
  "NIMBUSWARE_MAX_VRAM_PCT",
  "NIMBUSWARE_HW_AUTO_ADJUST",
]);

function labelForKey(catalog, key) {
  const groups = catalog?.groups;
  if (!groups || typeof groups !== "object") return key;
  for (const defs of Object.values(groups)) {
    if (!Array.isArray(defs)) continue;
    for (const item of defs) {
      if (item?.key === key && item?.label) return `${item.label} (${key})`;
    }
  }
  return key;
}

function storedValue(stored, key, fallback) {
  if (stored && stored[key] != null && stored[key] !== "") return String(stored[key]);
  return fallback;
}

function truthySetting(raw) {
  const v = String(raw ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}

function renderGovernorPreview(gov) {
  const el = document.querySelector("#governor-preview");
  if (!el || !gov) return;
  const parallel = gov.max_parallel_writer_stages ?? "—";
  const tier = gov.hardware_tier ?? "—";
  el.textContent = `Effective preview: tier ${tier}, max parallel writer stages ${parallel}`;
}

export async function mountSettings(root) {
  const [me, catalog] = await Promise.all([
    apiJson("/settings/me"),
    apiJson("/settings/catalog").catch(() => null),
  ]);
  const stored = me.stored || me.values || me.settings || me;

  root.innerHTML = `
    <section id="governor-panel" class="panel">
      <h3>Resource governor</h3>
      <p id="governor-hardware-summary" class="muted"></p>
      <form id="governor-form">
        <label>
          Max system RAM %
          <input type="range" id="gov-ram-pct" name="NIMBUSWARE_MAX_SYSTEM_RAM_PCT" min="50" max="95" step="1" />
          <span id="gov-ram-pct-val"></span>
        </label>
        <label>
          Max VRAM %
          <input type="range" id="gov-vram-pct" name="NIMBUSWARE_MAX_VRAM_PCT" min="50" max="95" step="1" />
          <span id="gov-vram-pct-val"></span>
        </label>
        <label>
          <input type="checkbox" id="gov-auto-adjust" name="NIMBUSWARE_HW_AUTO_ADJUST" />
          Auto-adjust limits to detected hardware tier
        </label>
        <p id="governor-preview" class="muted"></p>
        <button type="submit" class="primary">Save governor</button>
      </form>
    </section>
    <form id="settings-form"></form>
    <section id="settings-launch-check" class="launch-panel">
      <h3>Launch readiness</h3>
      <p class="muted" id="settings-launch-run-hint" data-testid="maker-settings-launch-run-hint"></p>
      <div class="actions">
        <button type="button" id="settings-run-launch-eval" data-testid="maker-settings-run-launch-eval">Run launch check</button>
      </div>
      <div id="settings-launch-scorecard" class="launch-scorecard" data-testid="maker-settings-launch-scorecard"></div>
    </section>
    <section id="settings-compute-sharing" class="panel" data-testid="maker-settings-compute-sharing">
      <h3>Compute sharing</h3>
      <p class="muted">Distributed mesh defaults for collaborative sessions.</p>
      <label>
        <input type="checkbox" id="settings-compute-default-share" data-testid="maker-settings-compute-default-share" />
        Default when joining others' sessions: share my compute
      </label>
      <label>
        Default workload mode for new sessions
        <select id="settings-compute-workload-mode" data-testid="maker-settings-compute-workload-mode">
          <option value="host_only">Host only</option>
          <option value="manual_claim" selected>Manual claim</option>
          <option value="auto_share">Auto share</option>
          <option value="auto_optimize">Auto optimize</option>
        </select>
      </label>
      <label>
        Scheduling policy (auto share / optimize)
        <select id="settings-compute-spread-policy" data-testid="maker-settings-compute-spread-policy">
          <option value="spread" selected>Spread</option>
          <option value="pack">Pack</option>
        </select>
      </label>
    </section>
    <section id="settings-optimizer-weights" class="panel" data-testid="maker-settings-optimizer-weights">
      <h3>Auto-optimize weights</h3>
      <p class="muted">Priority mix when workload mode is Auto optimize (fo1788).</p>
      <div id="settings-optimizer-fields"></div>
      <div class="actions">
        <button type="button" id="settings-optimizer-save" class="secondary" data-testid="maker-settings-optimizer-save">
          Save weights
        </button>
      </div>
    </section>
    <section id="settings-agent-models" class="panel" data-testid="maker-settings-agent-models">
      <h3>Agent &amp; Models</h3>
      <p class="muted">
        Per-role provider bindings. API keys are configured in
        <a href="#/models?section=api-connections">Model Hub → API connections</a>.
      </p>
      <div id="settings-agent-models-table"></div>
      <div class="actions">
        <button type="button" id="settings-agent-models-save" class="primary" data-testid="maker-settings-agent-models-save">
          Save bindings
        </button>
      </div>
    </section>
    <section id="settings-routing-panel" class="panel" data-testid="maker-settings-routing-presets">
      <h3>Hybrid model routing</h3>
      <p class="muted" id="settings-routing-active" data-testid="maker-settings-routing-active"></p>
      <label>
        Preset
        <select id="settings-routing-select" data-testid="maker-settings-routing-select"></select>
      </label>
      <p class="muted" id="settings-routing-cloud" data-testid="maker-settings-routing-cloud"></p>
      <button type="button" id="settings-routing-apply" class="primary" data-testid="maker-settings-routing-apply">
        Apply routing preset
      </button>
    </section>
    <section id="settings-chat-panel" class="panel" data-testid="maker-settings-chat-panel">
      <h3>Chat</h3>
      <label>
        <input type="checkbox" id="settings-chat-resume" data-testid="maker-settings-chat-resume" />
        Resume last chat session when opening the Chat tab
      </label>
    </section>
    <section id="settings-trust-panel" class="panel" data-testid="maker-settings-trust-panel">
      <h3>Trust / Autopilot defaults</h3>
      <p class="muted">Patch runs default to Nimble (8); factory runs default to Continuous improve (10). Saved profile overrides at Chat start.</p>
      <label>
        Default saved profile
        <select id="settings-default-autopilot-profile" data-testid="maker-settings-default-autopilot-profile">
          <option value="">— none —</option>
        </select>
      </label>
    </section>
    <section id="settings-enforcement-panel" class="panel" data-testid="maker-settings-enforcement-panel">
      <h3>Enforcement depth defaults</h3>
      <p class="muted">Saved enforcement profile applied at Chat run start (orthogonal to trust/autopilot).</p>
      <label>
        Default saved profile
        <select id="settings-default-enforcement-profile" data-testid="maker-settings-default-enforcement-profile">
          <option value="">— none —</option>
        </select>
      </label>
    </section>
    <section id="settings-memory-library" class="panel" data-testid="maker-settings-memory-library">
      <h3>Memory library</h3>
      <p class="muted" id="settings-memory-caption"></p>
      <button type="button" id="settings-memory-refresh" data-testid="maker-settings-memory-refresh">Refresh chunks</button>
      <ul id="settings-memory-chunks" class="memory-chunk-list"></ul>
    </section>
    <section id="settings-stitch-panel" class="panel" data-testid="maker-settings-stitch-panel">
      <h3>Stitch / catalog integrator</h3>
      <p class="muted">Promote research catalog candidates into the bundle catalog (requires admin token).</p>
      <button type="button" id="settings-stitch-refresh" data-testid="maker-settings-stitch-refresh">Load candidates</button>
      <button type="button" id="settings-stitch-batch" data-testid="maker-settings-stitch-batch-promote">Promote pending stitch batch</button>
      <ul id="settings-stitch-candidates"></ul>
    </section>
    <section id="settings-critic-reliability" class="panel" data-testid="maker-settings-critic-reliability">
      <h3>Critic reliability</h3>
      <div id="settings-critic-mount"></div>
      <details class="persona-probation-details">
        <summary>Persona probation metrics</summary>
        <label>Shelf <input type="text" id="settings-critic-shelf" value="development" /></label>
        <label>Persona ID <input type="text" id="settings-critic-persona" placeholder="persona id" /></label>
        <button type="button" id="settings-critic-probation" data-testid="maker-settings-critic-probation">Load probation reliability</button>
        <pre id="settings-critic-probation-body" class="json-pre"></pre>
      </details>
    </section>
    <p class="muted" id="reresearch-help">
      <strong>Re-research on plan fail</strong> (<code>NIMBUSWARE_RERESARCH_MISSING_CONTEXT</code>):
      when enabled, the pipeline may re-run research after planner missing-context failures.
    </p>`;

  async function refreshRoutingPresets() {
    const activeEl = root.querySelector("#settings-routing-active");
    const cloudEl = root.querySelector("#settings-routing-cloud");
    const select = root.querySelector("#settings-routing-select");
    if (!select) return;
    try {
      const body = await apiJson("/platform/routing-presets");
      const presets = body.presets || [];
      const active = String(body.active_preset_id || "local_only");
      select.replaceChildren();
      for (const preset of presets) {
        const opt = document.createElement("option");
        opt.value = String(preset.id || "");
        opt.textContent = String(preset.label || preset.id || "");
        if (opt.value === active) opt.selected = true;
        select.appendChild(opt);
      }
      if (activeEl) {
        activeEl.textContent = `Active preset: ${active}`;
      }
      const probe = body.cloud_preflight || {};
      if (cloudEl) {
        const ok = probe.ok === true;
        cloudEl.textContent = ok
          ? "Cloud preflight: ready"
          : `Cloud preflight: ${probe.message || probe.reason || "not configured"}`;
      }
    } catch (e) {
      if (activeEl) activeEl.textContent = "Routing presets unavailable";
      if (cloudEl) cloudEl.textContent = String(e.message || e);
    }
  }
  await refreshRoutingPresets();

  let agentBindingsState = { version: 1, roles: {} };
  let agentProviders = [];

  async function refreshAgentModels() {
    const host = root.querySelector("#settings-agent-models-table");
    if (!host) return;
    try {
      const body = await apiJson("/platform/model-bindings/defaults");
      agentBindingsState = body.defaults || { version: 1, roles: {} };
      agentProviders = body.providers || [];
      const rows = body.roles || [];
      const table = document.createElement("table");
      table.className = "data-table";
      table.innerHTML =
        "<thead><tr><th>Agent role</th><th>Provider</th><th>Model</th></tr></thead>";
      const tbody = document.createElement("tbody");
      for (const row of rows) {
        const role = row.agent_role || "";
        const binding = row.binding || agentBindingsState.roles?.[role] || {};
        const tr = document.createElement("tr");
        tr.dataset.testid = `maker-settings-agent-row-${role}`;
        const providerSelect = document.createElement("select");
        providerSelect.dataset.role = role;
        providerSelect.dataset.field = "provider_id";
        const cloudProviders = agentProviders.filter((p) => p.kind !== "local");
        for (const opt of [{ id: "ollama", label: "Ollama" }, ...cloudProviders]) {
          const o = document.createElement("option");
          o.value = opt.id;
          o.textContent = opt.label || opt.id;
          if ((binding.provider_id || "ollama") === o.value) o.selected = true;
          providerSelect.appendChild(o);
        }
        const modelInput = document.createElement("input");
        modelInput.dataset.role = role;
        modelInput.dataset.field = "model_id";
        modelInput.value = binding.model_id || "";
        modelInput.placeholder = "model id";
        tr.innerHTML = `<td>${row.display_name || role}</td>`;
        const pCell = document.createElement("td");
        pCell.appendChild(providerSelect);
        const mCell = document.createElement("td");
        mCell.appendChild(modelInput);
        tr.appendChild(pCell);
        tr.appendChild(mCell);
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      host.replaceChildren(table);
    } catch (e) {
      host.textContent = String(e.message || e);
    }
  }

  root.querySelector("#settings-agent-models-save")?.addEventListener("click", async () => {
    const host = root.querySelector("#settings-agent-models-table");
    if (!host) return;
    const roles = { ...(agentBindingsState.roles || {}) };
    host.querySelectorAll("[data-role][data-field]").forEach((el) => {
      const role = el.dataset.role;
      const field = el.dataset.field;
      if (!role || !field) return;
      const block = { ...(roles[role] || {}) };
      if (field === "provider_id") {
        block.provider_id = el.value;
        block.provider_kind = el.value === "ollama" ? "local" : "cloud";
      } else {
        block[field] = el.value;
      }
      roles[role] = block;
    });
    try {
      await apiJson("/platform/model-bindings/defaults", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: 1, roles }),
      });
      toast("Agent model bindings saved", "success");
      await refreshAgentModels();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  await refreshAgentModels();

  root.querySelector("#settings-routing-apply")?.addEventListener("click", async () => {
    const select = root.querySelector("#settings-routing-select");
    const presetId = select?.value?.trim();
    if (!presetId) return;
    try {
      const applied = await apiJson("/platform/routing-presets/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset_id: presetId }),
      });
      toast(`Applied routing preset: ${applied.preset_id || presetId}`, "success");
      await refreshRoutingPresets();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  const chatResume = root.querySelector("#settings-chat-resume");
  if (chatResume) {
    const resumeRaw = localStorage.getItem("maker_chat_resume_session");
    chatResume.checked = resumeRaw == null || resumeRaw === "1" || resumeRaw === "true";
    chatResume.addEventListener("change", () => {
      localStorage.setItem("maker_chat_resume_session", chatResume.checked ? "1" : "0");
      if (!chatResume.checked) sessionStorage.removeItem("maker_chat_session_id");
      toast("Chat session preference saved", "success");
    });
  }

  const DEFAULT_PROFILE_KEY = "maker_default_autopilot_profile_id";
  const trustSelect = root.querySelector("#settings-default-autopilot-profile");
  if (trustSelect) {
    try {
      const body = await apiJson("/platform/autopilot/user-profiles");
      for (const p of body.profiles || []) {
        const opt = document.createElement("option");
        opt.value = p.profile_id;
        opt.textContent = p.name || p.profile_id;
        trustSelect.appendChild(opt);
      }
    } catch {
      /* optional */
    }
    const savedProfile = localStorage.getItem(DEFAULT_PROFILE_KEY) || "";
    if (savedProfile) trustSelect.value = savedProfile;
    trustSelect.addEventListener("change", () => {
      const val = trustSelect.value?.trim() || "";
      if (val) localStorage.setItem(DEFAULT_PROFILE_KEY, val);
      else localStorage.removeItem(DEFAULT_PROFILE_KEY);
      toast("Default trust profile saved", "success");
    });
  }

  const DEFAULT_ENFORCEMENT_PROFILE_KEY = "maker_default_enforcement_profile_id";
  const enforcementSelect = root.querySelector("#settings-default-enforcement-profile");
  if (enforcementSelect) {
    try {
      const body = await apiJson("/platform/enforcement/user-profiles");
      for (const p of body.profiles || []) {
        const opt = document.createElement("option");
        opt.value = p.profile_id;
        opt.textContent = p.name || p.profile_id;
        enforcementSelect.appendChild(opt);
      }
    } catch {
      /* optional */
    }
    const savedEnforcement = localStorage.getItem(DEFAULT_ENFORCEMENT_PROFILE_KEY) || "";
    if (savedEnforcement) enforcementSelect.value = savedEnforcement;
    enforcementSelect.addEventListener("change", () => {
      const val = enforcementSelect.value?.trim() || "";
      if (val) localStorage.setItem(DEFAULT_ENFORCEMENT_PROFILE_KEY, val);
      else localStorage.removeItem(DEFAULT_ENFORCEMENT_PROFILE_KEY);
      toast("Default enforcement profile saved", "success");
    });
  }

  const ramPct = storedValue(stored, "NIMBUSWARE_MAX_SYSTEM_RAM_PCT", "75");
  const vramPct = storedValue(stored, "NIMBUSWARE_MAX_VRAM_PCT", "85");
  const autoAdjust = truthySetting(storedValue(stored, "NIMBUSWARE_HW_AUTO_ADJUST", "1"));

  const ramInput = root.querySelector("#gov-ram-pct");
  const vramInput = root.querySelector("#gov-vram-pct");
  const autoInput = root.querySelector("#gov-auto-adjust");
  if (ramInput) ramInput.value = ramPct;
  if (vramInput) vramInput.value = vramPct;
  if (autoInput) autoInput.checked = autoAdjust;

  function syncSliderLabels() {
    const ramVal = root.querySelector("#gov-ram-pct-val");
    const vramVal = root.querySelector("#gov-vram-pct-val");
    if (ramVal && ramInput) ramVal.textContent = `${ramInput.value}%`;
    if (vramVal && vramInput) vramVal.textContent = `${vramInput.value}%`;
  }
  syncSliderLabels();
  ramInput?.addEventListener("input", syncSliderLabels);
  vramInput?.addEventListener("input", syncSliderLabels);

  async function refreshHardwarePreview() {
    try {
      const hw = await apiJson("/platform/hardware");
      const profile = hw.profile || {};
      const summary = root.querySelector("#governor-hardware-summary");
      if (summary) {
        const tier = profile.tier || "unknown";
        const total = profile.ram_total_gb != null ? `${profile.ram_total_gb} GB total` : "RAM n/a";
        const avail = profile.ram_available_gb != null ? `${profile.ram_available_gb} GB free` : "";
        summary.textContent = `Hardware tier: ${tier} · ${total}${avail ? ` · ${avail}` : ""}`;
      }
      renderGovernorPreview(hw.resource_governor);
    } catch {
      /* optional */
    }
  }
  await refreshHardwarePreview();

  root.querySelector("#governor-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const patch = {
      NIMBUSWARE_MAX_SYSTEM_RAM_PCT: String(ramInput?.value || "75"),
      NIMBUSWARE_MAX_VRAM_PCT: String(vramInput?.value || "85"),
      NIMBUSWARE_HW_AUTO_ADJUST: autoInput?.checked ? "1" : "0",
    };
    await apiJson("/settings/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: patch }),
    });
    toast("Governor settings saved", "success");
    await refreshHardwarePreview();
  });

  const form = root.querySelector("#settings-form");
  const entries = Object.entries(stored).filter(
    ([key, val]) =>
      !GOVERNOR_KEYS.has(key) &&
      (typeof val === "string" || typeof val === "number" || typeof val === "boolean"),
  );
  for (const [key, val] of entries) {
    const label = document.createElement("label");
    label.textContent = labelForKey(catalog, key);
    const input = document.createElement("input");
    input.name = key;
    input.value = String(val);
    label.appendChild(input);
    form?.appendChild(label);
  }
  const btn = document.createElement("button");
  btn.type = "submit";
  btn.textContent = "Save other settings";
  btn.className = "primary";
  form?.appendChild(btn);

  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    const patch = Object.fromEntries(fd.entries());
    await apiJson("/settings/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: patch }),
    });
    toast("Settings saved", "success");
  });

  let presetRunId = resolveRunId();
  if (!presetRunId) presetRunId = await hydrateActiveRun(apiJson);
  const launchHint = root.querySelector("#settings-launch-run-hint");
  if (launchHint) {
    launchHint.textContent = presetRunId
      ? `Using active run ${presetRunId} from session.`
      : "Select a project and start a run to enable launch check without pasting a UUID.";
  }

  root.querySelector("#settings-run-launch-eval")?.addEventListener("click", async () => {
    let id = resolveRunId();
    if (!id) id = await hydrateActiveRun(apiJson);
    if (!id) return toast("No active run — open Progress or start a build", "error");
    const body = root.querySelector("#settings-launch-scorecard");
    try {
      const scorecard = await apiJson(`/runs/${encodeURIComponent(id)}/maker/launch-eval`, {
        method: "POST",
      });
      renderLaunchScorecard(body, scorecard, { testIdPrefix: "maker-settings" });
      toast("Launch check complete", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  async function loadMemoryChunks() {
    const projectId = getActiveProjectId();
    const list = root.querySelector("#settings-memory-chunks");
    const caption = root.querySelector("#settings-memory-caption");
    if (!projectId) {
      if (caption) caption.textContent = "Select a project on Home to browse memory chunks.";
      list?.replaceChildren();
      return;
    }
    try {
      const body = await apiJson(`/memory/chunks?project_id=${encodeURIComponent(projectId)}&limit=50`);
      if (caption) caption.textContent = body.caption || `${body.total || 0} chunks`;
      list?.replaceChildren();
      for (const ch of body.chunks || []) {
        const li = document.createElement("li");
        li.className = "memory-chunk-card";
        li.dataset.testid = "maker-settings-memory-chunk";
        li.innerHTML = `<strong>${ch.category || ch.source_event_type || "chunk"}</strong>
          <span class="muted">${ch.severity || ""} · run ${String(ch.run_id || "").slice(0, 8)}</span>
          <p class="memory-chunk-preview">${ch.excerpt || ""}</p>`;
        const insertBtn = document.createElement("button");
        insertBtn.type = "button";
        insertBtn.textContent = "Insert into active run";
        insertBtn.dataset.testid = "maker-settings-memory-insert";
        insertBtn.addEventListener("click", async () => {
          let runId = resolveRunId();
          if (!runId) runId = await hydrateActiveRun(apiJson);
          if (!runId) return toast("No active run — open Progress or start a build", "error");
          try {
            await apiJson(
              `/runs/${encodeURIComponent(runId)}/memory-chunks/${encodeURIComponent(ch.chunk_id)}/insert`,
              { method: "POST" },
            );
            toast("Memory chunk inserted into run context", "success");
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        });
        li.appendChild(insertBtn);
        list?.appendChild(li);
      }
      if (!(body.chunks || []).length) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "No memory chunks indexed for this workspace yet.";
        list?.appendChild(li);
      }
    } catch (e) {
      if (caption) caption.textContent = String(e.message || e);
    }
  }
  root.querySelector("#settings-memory-refresh")?.addEventListener("click", () => {
    loadMemoryChunks().catch((e) => toast(String(e.message), "error"));
  });
  await loadMemoryChunks();

  let catalogVersion = 1;
  async function loadStitchCandidates() {
    const ul = root.querySelector("#settings-stitch-candidates");
    ul?.replaceChildren();
    try {
      const [candBody, catalogBody] = await Promise.all([
        apiJson("/bundles/catalog-candidates?limit=50"),
        apiJson("/bundles/catalog").catch(() => ({ document_version: 1 })),
      ]);
      catalogVersion = catalogBody.document_version ?? 1;
      for (const c of candBody.candidates || []) {
        const li = document.createElement("li");
        li.dataset.testid = "maker-settings-stitch-candidate";
        const label = `${c.candidate_id || c.id || "?"} (${c.run_id || "?"}) — ${c.status || "pending"}`;
        li.textContent = label;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Promote";
        btn.dataset.testid = "maker-settings-stitch-promote-one";
        btn.addEventListener("click", async () => {
          try {
            await apiJson(
              `/bundles/catalog-candidates/${encodeURIComponent(c.run_id)}/${encodeURIComponent(c.candidate_id)}/promote?expected_version=${catalogVersion}`,
              { method: "POST" },
            );
            toast("Candidate promoted", "success");
            await loadStitchCandidates();
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        });
        li.appendChild(btn);
        ul?.appendChild(li);
      }
      if (!(candBody.candidates || []).length) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "No catalog candidates (admin token may be required).";
        ul?.appendChild(li);
      }
    } catch (e) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = String(e.message || e);
      ul?.appendChild(li);
    }
  }
  root.querySelector("#settings-stitch-refresh")?.addEventListener("click", () => {
    loadStitchCandidates().catch((e) => toast(String(e.message), "error"));
  });
  root.querySelector("#settings-stitch-batch")?.addEventListener("click", async () => {
    try {
      await apiJson(
        `/bundles/catalog-candidates/promote-stitch-pending?expected_version=${catalogVersion}`,
        { method: "POST" },
      );
      toast("Batch promote complete", "success");
      await loadStitchCandidates();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  if (presetRunId) {
    try {
      const criticBody = await loadRunOrFleetCriticReliability(apiJson, presetRunId);
      renderCriticReliabilityPanel(root.querySelector("#settings-critic-mount"), criticBody, {
        testIdPrefix: "maker-settings-critic",
      });
    } catch {
      renderCriticReliabilityPanel(root.querySelector("#settings-critic-mount"), {}, {
        testIdPrefix: "maker-settings-critic",
      });
    }
  }

  root.querySelector("#settings-critic-probation")?.addEventListener("click", async () => {
    const shelf = root.querySelector("#settings-critic-shelf")?.value?.trim();
    const persona = root.querySelector("#settings-critic-persona")?.value?.trim();
    if (!shelf || !persona) return toast("Enter shelf and persona id", "error");
    const pre = root.querySelector("#settings-critic-probation-body");
    try {
      const body = await apiJson(
        `/personas/${encodeURIComponent(shelf)}/${encodeURIComponent(persona)}/probation-reliability`,
      );
      if (pre) pre.textContent = JSON.stringify(body, null, 2);
    } catch (e) {
      if (pre) pre.textContent = String(e.message || e);
    }
  });

  const optimizerFields = root.querySelector("#settings-optimizer-fields");
  const optimizerKeys = ["headroom", "model_fit", "latency", "cost"];
  if (optimizerFields) {
    optimizerFields.replaceChildren();
    for (const key of optimizerKeys) {
      const label = document.createElement("label");
      label.textContent = `${key} `;
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.max = "1";
      input.step = "0.05";
      input.dataset.optimizerKey = key;
      input.dataset.testid = `maker-settings-optimizer-${key}`;
      label.appendChild(input);
      optimizerFields.appendChild(label);
    }
    try {
      const body = await apiJson("/platform/optimizer-weights");
      const weights = body.weights || {};
      for (const input of optimizerFields.querySelectorAll("input[data-optimizer-key]")) {
        const k = input.dataset.optimizerKey;
        if (k && weights[k] != null) input.value = String(weights[k]);
      }
    } catch {
      /* defaults in UI */
    }
  }
  root.querySelector("#settings-optimizer-save")?.addEventListener("click", async () => {
    const weights = {};
    for (const input of optimizerFields?.querySelectorAll("input[data-optimizer-key]") || []) {
      weights[input.dataset.optimizerKey] = Number(input.value) || 0;
    }
    try {
      await apiJson("/platform/optimizer-weights", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights }),
      });
      toast("Optimizer weights saved", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
