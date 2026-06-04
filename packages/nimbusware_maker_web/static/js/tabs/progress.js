import { apiJson, toast } from "../api-client.js";
import { openSseStream, parseSseJson } from "../sse-client.js";

function runId() {
  return document.getElementById("run-theater-run-id")?.value?.trim() || "";
}

let theaterHandle = null;
let progressHandle = null;

export async function mountProgress(root) {
  const mount = document.getElementById("progress-mount");
  if (mount) {
    mount.innerHTML = `
      <ul id="theater-list"></ul>
      <p id="slice-summary"></p>
      <ol id="slice-list"></ol>
      <h4>Memory influence</h4>
      <table id="memory-influence-table"><thead><tr><th>Stage</th><th>Hits</th><th>Digest</th></tr></thead><tbody></tbody></table>`;
  }

  function stopStreams() {
    theaterHandle?.close();
    progressHandle?.close();
    theaterHandle = null;
    progressHandle = null;
  }

  function appendTheater(msg) {
    const list = document.getElementById("theater-list");
    if (!list || !msg) return;
    const li = document.createElement("li");
    li.textContent = `${msg.actor_display || "System"}: ${msg.headline || ""}`;
    list.appendChild(li);
  }

  function renderProgress(body) {
    const summary = document.getElementById("slice-summary");
    const list = document.getElementById("slice-list");
    if (summary) {
      summary.textContent = body.current_headline || body.run_status || "";
    }
    if (list) {
      list.replaceChildren();
      for (const s of body.slices || []) {
        const li = document.createElement("li");
        li.textContent = `${s.headline || s.slice_id} — ${s.status || s.state || ""}`;
        list.appendChild(li);
      }
    }
  }

  window.addEventListener("maker-route-leave-progress", stopStreams);

  const id = runId();
  if (!id) return;

  theaterHandle = openSseStream(`/runs/${id}/theater/stream`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data?.message) appendTheater(data.message);
      else if (data?.messages) data.messages.forEach(appendTheater);
    },
  });

  progressHandle = openSseStream(`/runs/${id}/maker-progress/stream?simple=true`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data) renderProgress(data);
    },
  });

  try {
    const snap = await apiJson(`/runs/${id}/maker-progress?simple=true`);
    renderProgress(snap);
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  try {
    const mem = await apiJson(`/runs/${id}/memory-influence`);
    const tbody = document.querySelector("#memory-influence-table tbody");
    if (tbody) {
      tbody.replaceChildren();
      for (const row of mem.rows || []) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${row.stage || ""}</td><td>${row.hits || ""}</td><td>${row.query_digest || ""}</td>`;
        tbody.appendChild(tr);
      }
    }
  } catch {
    /* optional panel when run has no retrieval events */
  }
}

export function unmountProgress() {
  window.dispatchEvent(new Event("maker-route-leave-progress"));
}
