/**
 * Progress / review panels (poll + approval) until full tab modules ship.
 */
import { apiJson, toast } from "./api-client.js";

function runId() {
  return document.getElementById("run-theater-run-id")?.value?.trim() || "";
}

function setStatus(text) {
  const el = document.getElementById("status");
  if (el) el.textContent = text;
}

function ensureProgressPanels() {
  const mount = document.getElementById("progress-mount");
  if (!mount || mount.dataset.ready) return;
  mount.dataset.ready = "1";
  mount.innerHTML = `
    <div class="actions">
      <button type="button" id="btn-load-theater">Load theater</button>
      <button type="button" id="btn-load-research">Load research</button>
      <button type="button" id="btn-load-slices">Load slices</button>
      <button type="button" id="btn-load-pending">Load approval</button>
    </div>
    <section class="panel" id="approval-panel"><h3>Slice approval</h3>
      <p id="approval-summary"></p><div id="approval-actions" class="actions"></div></section>
    <section class="panel"><h3>Slice progress</h3><p id="slice-summary"></p><ol id="slice-list"></ol></section>
    <section class="panel"><h3>Theater</h3><ul id="theater-list"></ul></section>
    <section class="panel"><h3>Research</h3><ul id="research-list"></ul></section>`;
  bindProgressButtons();
}

function bindProgressButtons() {
  const bind = (id, fn) => {
    document.getElementById(id)?.addEventListener("click", () => fn().catch((e) => setStatus(String(e.message || e))));
  };
  bind("btn-load-theater", loadTheater);
  bind("btn-load-research", loadResearch);
  bind("btn-load-slices", loadSlices);
  bind("btn-load-pending", loadPending);
}

async function loadTheater() {
  const id = runId();
  if (!id) return setStatus("Enter a run ID.");
  const body = await apiJson(`/runs/${id}/theater?limit=200`);
  const list = document.getElementById("theater-list");
  if (!list) return;
  list.replaceChildren();
  for (const msg of body.messages || []) {
    const li = document.createElement("li");
    li.textContent = `[${msg.store_seq ?? ""}] ${msg.actor_display || "System"}: ${msg.headline || ""}`;
    list.appendChild(li);
  }
  setStatus(`Theater: ${body.count ?? 0} messages`);
}

async function loadResearch() {
  const id = runId();
  if (!id) return setStatus("Enter a run ID.");
  const body = await apiJson(`/runs/${id}/research`);
  const list = document.getElementById("research-list");
  if (!list) return;
  list.replaceChildren();
  for (const brief of body.briefs || []) {
    const li = document.createElement("li");
    const bid = brief.brief_id || brief.artifact_id || "?";
    const status = brief.review_status || brief.status || "";
    li.textContent = `${brief.brief_kind || ""} ${bid} — ${status}`;
    if (status === "pending") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Approve";
      btn.onclick = async () => {
        await apiJson(`/runs/${id}/research/${encodeURIComponent(bid)}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ notes: "Approved via Maker web" }),
        });
        toast("Brief approved", "success");
        await loadResearch();
      };
      li.appendChild(btn);
    }
    list.appendChild(li);
  }
}

async function loadSlices() {
  const id = runId();
  if (!id) return setStatus("Enter a run ID.");
  const body = await apiJson(`/runs/${id}/maker-progress?simple=true`);
  const summary = document.getElementById("slice-summary");
  const list = document.getElementById("slice-list");
  if (summary) {
    summary.textContent = `Slice ${(body.slice_index ?? 0) + 1}/${body.slice_total ?? 0} — ${body.current_headline || ""}`;
  }
  if (list) {
    list.replaceChildren();
    for (const s of body.slices || []) {
      const li = document.createElement("li");
      li.textContent = `${s.headline || s.slice_id || "slice"} — ${s.status || s.state || ""}`;
      list.appendChild(li);
    }
  }
}

async function loadPending() {
  const id = runId();
  if (!id) return setStatus("Enter a run ID.");
  const body = await apiJson(`/runs/${id}/maker/pending`);
  const summary = document.getElementById("approval-summary");
  const actions = document.getElementById("approval-actions");
  if (summary) {
    summary.textContent = body.plan_approved ? "Plan approved" : "Plan not approved";
  }
  if (!actions) return;
  actions.replaceChildren();
  if (!body.plan_approved) {
    const btn = document.createElement("button");
    btn.textContent = "Approve plan";
    btn.onclick = async () => {
      await apiJson(`/runs/${id}/maker/plan/approve`, { method: "POST" });
      await loadPending();
    };
    actions.appendChild(btn);
  }
  const pending = body.pending || null;
  if (body.awaiting_approval && pending) {
    const sliceId = pending.slice_id || pending.id;
    if (sliceId) {
      const apply = document.createElement("button");
      apply.textContent = "Apply slice";
      apply.onclick = async () => {
        await apiJson(`/runs/${id}/maker/slices/apply`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slice_id: String(sliceId) }),
        });
        await loadPending();
      };
      actions.appendChild(apply);
      const skip = document.createElement("button");
      skip.textContent = "Skip slice";
      skip.onclick = async () => {
        await apiJson(`/runs/${id}/maker/slices/skip`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slice_id: String(sliceId) }),
        });
        await loadPending();
      };
      actions.appendChild(skip);
    }
  } else if (body.plan_approved && !body.awaiting_approval) {
    const prep = document.createElement("button");
    prep.textContent = "Prepare next slice";
    prep.onclick = async () => {
      await apiJson(`/runs/${id}/maker/slices/prepare`, { method: "POST" });
      await loadPending();
    };
    actions.appendChild(prep);
  }
}

window.addEventListener("maker-route", () => {
  if (window.location.hash.includes("/progress") || parseRoute() === "/progress") {
    ensureProgressPanels();
  }
});

function parseRoute() {
  const hash = window.location.hash.replace(/^#/, "") || "/home";
  return hash.split("?")[0] || "/home";
}

ensureProgressPanels();
