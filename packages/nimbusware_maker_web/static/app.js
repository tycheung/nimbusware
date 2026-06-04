const API_PREFIX = "/v1";

function runId() {
  return document.getElementById("run-theater-run-id").value.trim();
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

async function apiJson(path, options = {}) {
  const res = await fetch(`${API_PREFIX}${path}`, {
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err.slice(0, 200)}`);
  }
  return res.json();
}

function renderTheater(messages) {
  const list = document.getElementById("theater-list");
  list.replaceChildren();
  for (const msg of messages) {
    const li = document.createElement("li");
    const actor = msg.actor_display || "System";
    const headline = msg.headline || "";
    const severity = msg.severity || "info";
    const seq = msg.store_seq ?? "";
    li.innerHTML = `<div class="theater-headline">[${seq}] ${actor} (${severity}): ${headline}</div>`;
    if (msg.body_md) {
      const body = document.createElement("div");
      body.className = "theater-body";
      body.textContent = msg.body_md;
      li.appendChild(body);
    }
    list.appendChild(li);
  }
}

function renderResearch(briefs) {
  const list = document.getElementById("research-list");
  list.replaceChildren();
  for (const brief of briefs) {
    const li = document.createElement("li");
    const id = brief.brief_id || brief.artifact_id || "?";
    const status = brief.review_status || brief.status || "unknown";
    const kind = brief.brief_kind || "";
    li.textContent = `${kind} brief ${id} — ${status}`;
    if (status === "pending") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Approve";
      btn.addEventListener("click", async () => {
        try {
          setStatus("Approving brief…");
          await apiJson(`/runs/${runId()}/research/${encodeURIComponent(id)}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: "Approved via Maker web" }),
          });
          setStatus("Brief approved.");
          await loadResearch();
        } catch (e) {
          setStatus(String(e.message || e));
        }
      });
      li.appendChild(document.createTextNode(" "));
      li.appendChild(btn);
    }
    list.appendChild(li);
  }
}

function renderSliceProgress(body) {
  const summary = document.getElementById("slice-summary");
  const list = document.getElementById("slice-list");
  list.replaceChildren();
  const total = body.slice_total ?? 0;
  const done = body.slices_completed ?? 0;
  const idx = body.slice_index ?? 0;
  const headline = body.current_headline || body.run_status || "";
  summary.textContent = total
    ? `Slice ${idx + 1}/${total} — ${done} completed. ${headline}`
    : headline || "No slice progress yet.";
  const slices = body.slices || [];
  for (const slice of slices) {
    const li = document.createElement("li");
    const label = slice.headline || slice.stage_name || slice.slice_id || "slice";
    const state = slice.status || slice.state || "";
    li.textContent = state ? `${label} — ${state}` : String(label);
    list.appendChild(li);
  }
}

function addActionButton(container, label, onClick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = label;
  btn.addEventListener("click", () => {
    onClick().catch((e) => setStatus(String(e.message || e)));
  });
  container.appendChild(btn);
}

function renderPending(body) {
  const summary = document.getElementById("approval-summary");
  const actions = document.getElementById("approval-actions");
  actions.replaceChildren();

  const parts = [];
  parts.push(body.plan_approved ? "Plan approved" : "Plan not approved yet");
  if (body.awaiting_approval) {
    parts.push("awaiting slice approval");
  }
  const pending = body.pending || null;
  if (pending) {
    const sid = pending.slice_id || pending.id || "?";
    const headline = pending.headline || pending.stage_name || sid;
    parts.push(`pending: ${headline}`);
  }
  summary.textContent = parts.join(" · ");

  const id = runId();
  if (!body.plan_approved) {
    addActionButton(actions, "Approve plan", async () => {
      setStatus("Approving plan…");
      await apiJson(`/runs/${id}/maker/plan/approve`, { method: "POST" });
      setStatus("Plan approved.");
      await loadPending();
      await loadSlices();
    });
  }

  if (body.awaiting_approval && pending) {
    const sliceId = pending.slice_id || pending.id;
    if (sliceId) {
      addActionButton(actions, "Apply slice", async () => {
        setStatus("Applying slice…");
        await apiJson(`/runs/${id}/maker/slices/apply`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slice_id: String(sliceId) }),
        });
        setStatus("Slice applied.");
        await loadPending();
        await loadSlices();
      });
      addActionButton(actions, "Skip slice", async () => {
        setStatus("Skipping slice…");
        await apiJson(`/runs/${id}/maker/slices/skip`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slice_id: String(sliceId) }),
        });
        setStatus("Slice skipped.");
        await loadPending();
        await loadSlices();
      });
    }
  } else if (body.plan_approved && !body.awaiting_approval) {
    addActionButton(actions, "Prepare next slice", async () => {
      setStatus("Preparing slice…");
      await apiJson(`/runs/${id}/maker/slices/prepare`, { method: "POST" });
      setStatus("Slice prepared.");
      await loadPending();
      await loadSlices();
    });
  }
}

async function loadTheater() {
  const id = runId();
  if (!id) {
    setStatus("Enter a run ID.");
    return;
  }
  setStatus("Loading theater…");
  const body = await apiJson(`/runs/${id}/theater?limit=200`);
  renderTheater(body.messages || []);
  setStatus(`Theater: ${body.count ?? 0} messages`);
}

async function loadResearch() {
  const id = runId();
  if (!id) {
    setStatus("Enter a run ID.");
    return;
  }
  setStatus("Loading research…");
  const body = await apiJson(`/runs/${id}/research`);
  renderResearch(body.briefs || []);
  setStatus(`Research: ${body.count ?? 0} briefs`);
}

async function loadSlices() {
  const id = runId();
  if (!id) {
    setStatus("Enter a run ID.");
    return;
  }
  setStatus("Loading slice progress…");
  const body = await apiJson(`/runs/${id}/maker-progress?simple=true`);
  renderSliceProgress(body);
  setStatus(`Slices: ${body.slices_completed ?? 0}/${body.slice_total ?? 0}`);
}

async function loadPending() {
  const id = runId();
  if (!id) {
    setStatus("Enter a run ID.");
    return;
  }
  setStatus("Loading approval state…");
  const body = await apiJson(`/runs/${id}/maker/pending`);
  renderPending(body);
  setStatus(
    body.awaiting_approval ? "Awaiting slice approval" : "Approval state loaded",
  );
}

document.getElementById("btn-load-theater").addEventListener("click", () => {
  loadTheater().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-load-research").addEventListener("click", () => {
  loadResearch().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-load-slices").addEventListener("click", () => {
  loadSlices().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-load-pending").addEventListener("click", () => {
  loadPending().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-poll-theater").addEventListener("click", () => {
  loadTheater().catch((e) => setStatus(String(e.message || e)));
});

const params = new URLSearchParams(window.location.search);
const fromQuery = params.get("run_id");
if (fromQuery) {
  document.getElementById("run-theater-run-id").value = fromQuery;
}
