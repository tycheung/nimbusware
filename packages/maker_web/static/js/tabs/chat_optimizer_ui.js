import { apiJson, toast } from "../api-client.js";

const OPTIMIZER_KEYS = ["headroom", "model_fit", "latency", "cost"];

const LABELS = {
  headroom: "Headroom",
  model_fit: "Model fit",
  latency: "Latency",
  cost: "Cost",
};

function mountPanel(root) {
  let panel = root.querySelector("[data-testid='maker-chat-optimizer-panel']");
  if (!panel) {
    panel = document.createElement("section");
    panel.className = "panel chat-optimizer-panel muted";
    panel.dataset.testid = "maker-chat-optimizer-panel";
    panel.innerHTML = `
      <h4>Optimizer priority</h4>
      <p class="muted chat-optimizer-hint">Drag to rank criteria (top = highest weight).</p>
      <ol class="chat-optimizer-list" data-testid="maker-chat-optimizer-list"></ol>
      <button type="button" class="btn btn--sm" data-testid="maker-chat-optimizer-save">Save priority</button>`;
    const compute = root.querySelector("#chat-compute-nodes");
    compute?.insertAdjacentElement("afterend", panel);
  }
  return panel;
}

function wireDragList(list, priority) {
  list.replaceChildren();
  for (const key of priority) {
    const li = document.createElement("li");
    li.className = "chat-optimizer-item";
    li.draggable = true;
    li.dataset.optimizerKey = key;
    li.dataset.testid = `maker-chat-optimizer-item-${key}`;
    li.textContent = LABELS[key] || key;
    li.addEventListener("dragstart", (ev) => {
      ev.dataTransfer?.setData("text/plain", key);
      li.classList.add("chat-optimizer-item--dragging");
    });
    li.addEventListener("dragend", () => li.classList.remove("chat-optimizer-item--dragging"));
    li.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      li.classList.add("chat-optimizer-item--over");
    });
    li.addEventListener("dragleave", () => li.classList.remove("chat-optimizer-item--over"));
    li.addEventListener("drop", (ev) => {
      ev.preventDefault();
      li.classList.remove("chat-optimizer-item--over");
      const from = ev.dataTransfer?.getData("text/plain");
      if (!from || from === key) return;
      const items = [...list.querySelectorAll(".chat-optimizer-item")].map((el) => el.dataset.optimizerKey);
      const fromIdx = items.indexOf(from);
      const toIdx = items.indexOf(key);
      if (fromIdx < 0 || toIdx < 0) return;
      items.splice(fromIdx, 1);
      items.splice(toIdx, 0, from);
      wireDragList(list, items);
    });
    list.appendChild(li);
  }
}

export async function refreshSessionOptimizerPanel(root, sessionId, { workloadMode = "host_only" } = {}) {
  const panel = mountPanel(root);
  const show = workloadMode === "auto_optimize" && Boolean(sessionId);
  panel.hidden = !show;
  if (!show) return;
  const list = panel.querySelector(".chat-optimizer-list");
  try {
    const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/optimizer-weights`);
    const priority = (body.priority || OPTIMIZER_KEYS).filter((k) => OPTIMIZER_KEYS.includes(k));
    wireDragList(list, priority.length ? priority : [...OPTIMIZER_KEYS]);
    const saveBtn = panel.querySelector("[data-testid='maker-chat-optimizer-save']");
    if (saveBtn && !saveBtn.dataset.wired) {
      saveBtn.dataset.wired = "1";
      saveBtn.addEventListener("click", async () => {
        const order = [...list.querySelectorAll(".chat-optimizer-item")].map(
          (el) => el.dataset.optimizerKey,
        );
        try {
          await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/optimizer-weights`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ priority: order }),
          });
          toast("Optimizer priority saved", "success");
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
    }
  } catch {
    wireDragList(list, [...OPTIMIZER_KEYS]);
  }
}
