import { apiJson, toast } from "../api-client.js";
import { toastIfMiss } from "../broker_miss.js";

function pendingRows(body) {
  const pending = body?.pending;
  return Array.isArray(pending) ? pending : [];
}

export async function mountEvolutionPanel(card, runId) {
  if (!card || !runId) return;
  let panel = card.querySelector("[data-testid='maker-chat-evolution-panel']");
  if (!panel) {
    panel = document.createElement("section");
    panel.className = "chat-evolution-panel panel";
    panel.dataset.testid = "maker-chat-evolution-panel";
    const theater = card.querySelector(".chat-run-card__theater");
    if (theater) card.insertBefore(panel, theater);
    else card.appendChild(panel);
  }

  const title = document.createElement("h4");
  title.textContent = "Evolution proposals";
  const refresh = document.createElement("button");
  refresh.type = "button";
  refresh.className = "linkish";
  refresh.textContent = "Refresh";
  refresh.dataset.testid = "maker-chat-evolution-refresh";
  const header = document.createElement("div");
  header.className = "chat-evolution-panel__header actions";
  header.append(title, refresh);
  const list = document.createElement("ul");
  list.className = "chat-evolution-list";
  list.dataset.testid = "maker-chat-evolution-list";
  const empty = document.createElement("p");
  empty.className = "muted";
  empty.dataset.testid = "maker-chat-evolution-empty";
  empty.textContent = "No pending evolution proposals yet.";

  panel.replaceChildren(header, empty, list);

  async function load() {
    const body = await apiJson(`/runs/${encodeURIComponent(runId)}/evolution`).catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "evolution",
    }));
    if (toastIfMiss(body, toast, "Evolution timeline unavailable")) {
      empty.textContent = "Evolution timeline unavailable";
      empty.hidden = false;
      list.replaceChildren();
      return;
    }
    const rows = pendingRows(body);
    list.replaceChildren();
    if (!rows.length) {
      empty.hidden = false;
      empty.textContent = "No pending evolution proposals yet.";
      return;
    }
    empty.hidden = true;
    for (const row of rows) {
      const li = document.createElement("li");
      li.className = "chat-evolution-item";
      const artifactId = String(row.artifact_id || row.id || "").trim();
      const label = document.createElement("span");
      label.textContent = `${row.layer || "evolution"} · ${artifactId || "proposal"}`.slice(0, 120);
      const actions = document.createElement("div");
      actions.className = "actions";
      const promote = document.createElement("button");
      promote.type = "button";
      promote.className = "primary";
      promote.textContent = "Promote";
      promote.dataset.testid = "maker-chat-evolution-promote";
      promote.disabled = !artifactId;
      promote.addEventListener("click", async () => {
        const res = await apiJson(`/runs/${encodeURIComponent(runId)}/evolution/promote`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ artifact_id: artifactId, promote: true }),
        }).catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "evolution_promote",
        }));
        if (toastIfMiss(res, toast, "Promote unavailable")) return;
        toast("Evolution artifact promoted", "success");
        await load();
      });
      const reject = document.createElement("button");
      reject.type = "button";
      reject.textContent = "Reject";
      reject.dataset.testid = "maker-chat-evolution-reject";
      reject.disabled = !artifactId;
      reject.addEventListener("click", async () => {
        const res = await apiJson(`/runs/${encodeURIComponent(runId)}/evolution/promote`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ artifact_id: artifactId, promote: false }),
        }).catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "evolution_promote",
        }));
        if (toastIfMiss(res, toast, "Reject unavailable")) return;
        toast("Evolution artifact rejected", "info");
        await load();
      });
      actions.append(promote, reject);
      li.append(label, actions);
      list.appendChild(li);
    }
  }

  refresh.addEventListener("click", () => {
    void load();
  });
  await load();
}
