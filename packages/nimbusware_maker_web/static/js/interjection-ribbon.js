import { apiJson, toast } from "./api-client.js";

export async function queueInterjection(runId, message, priority) {
  await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, priority }),
  });
}

export async function refreshInterjectionQueue(runId, queueBody) {
  if (!queueBody) return;
  try {
    const q = await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`);
    const items = q.queue?.items || [];
    queueBody.textContent = items.length
      ? items.map((i) => `[${i.priority}] ${i.message}`).join(" · ")
      : "Queue empty";
  } catch {
    queueBody.textContent = "";
  }
}

function interjectionEl(root, dataAttr, id) {
  return root.querySelector(`[${dataAttr}]`) || (id ? root.querySelector(`#${id}`) : null);
}

export function wireInterjectionRibbon(root, runId, { showQueue = true } = {}) {
  const message = interjectionEl(root, "data-interjection-message", "interjection-message")
    || interjectionEl(root, "data-interjection-message", "chat-interjection-message");
  const nextBtn = interjectionEl(root, "data-interjection-next", "interjection-next-btn")
    || interjectionEl(root, "data-interjection-next", "chat-interjection-next");
  const lastBtn = interjectionEl(root, "data-interjection-last", "interjection-last-btn")
    || interjectionEl(root, "data-interjection-last", "chat-interjection-last");
  const queueBody = showQueue
    ? interjectionEl(root, "data-interjection-queue-body", "interjection-queue-body")
    : null;
  if (!message || !runId) return;

  const post = async (priority) => {
    const msg = message.value?.trim();
    if (!msg) return toast("Enter a message", "error");
    try {
      await queueInterjection(runId, msg, priority);
      toast("Queued", "success");
      message.value = "";
      if (queueBody) await refreshInterjectionQueue(runId, queueBody);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  };

  nextBtn?.addEventListener("click", () => post("next"));
  lastBtn?.addEventListener("click", () => post("last"));
  if (queueBody) void refreshInterjectionQueue(runId, queueBody);
}

export function interjectionRibbonHtml({ rootId = "interjection-ribbon", compact = false } = {}) {
  const tag = compact ? "div" : "section";
  const idAttr = rootId ? ` id="${rootId}"` : "";
  const panelClass = compact ? "" : " panel";
  const queueLine = compact
    ? ""
    : `<p data-interjection-queue-body id="interjection-queue-body" class="muted"></p>`;
  return `
    <${tag}${idAttr} class="interjection-ribbon${panelClass}" data-testid="maker-interjection-ribbon">
      <h4>Interjection${compact ? "" : " queue"}</h4>
      <textarea data-interjection-message id="interjection-message" rows="2" placeholder="Steer the next slice…" data-testid="maker-interjection-input"></textarea>
      <div class="actions">
        <button type="button" data-interjection-next id="interjection-next-btn" data-testid="maker-interjection-next">${compact ? "Next" : "Next in queue"}</button>
        <button type="button" data-interjection-last id="interjection-last-btn" data-testid="maker-interjection-last">${compact ? "Last" : "Last in queue"}</button>
      </div>
      ${queueLine}
    </${tag}>`;
}

export function chatInterjectionRibbonHtml() {
  return `
    <div class="chat-interjection-ribbon panel" data-testid="maker-chat-interjection-ribbon">
      <h4>Interjection</h4>
      <textarea data-interjection-message id="chat-interjection-message" rows="2" placeholder="Steer the next slice…" data-testid="maker-chat-interjection-input"></textarea>
      <div class="actions">
        <button type="button" data-interjection-next id="chat-interjection-next" data-testid="maker-chat-interjection-next">Next</button>
        <button type="button" data-interjection-last id="chat-interjection-last" data-testid="maker-chat-interjection-last">Last</button>
      </div>
    </div>`;
}
