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

document.getElementById("btn-load-theater").addEventListener("click", () => {
  loadTheater().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-load-research").addEventListener("click", () => {
  loadResearch().catch((e) => setStatus(String(e.message || e)));
});

document.getElementById("btn-poll-theater").addEventListener("click", () => {
  loadTheater().catch((e) => setStatus(String(e.message || e)));
});

const params = new URLSearchParams(window.location.search);
const fromQuery = params.get("run_id");
if (fromQuery) {
  document.getElementById("run-theater-run-id").value = fromQuery;
}
