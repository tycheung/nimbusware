import { apiJson, toast } from "../api-client.js";

export function nodeHeadroom(node) {
  const caps = node.capabilities || {};
  const total = Number(caps.claims_total ?? caps.max_parallel_claims ?? 0);
  const used = Number(caps.claims_used ?? caps.active_claims ?? 0);
  if (total > 0) {
    const free = Math.max(0, total - used);
    return { text: `${free}/${total} free`, low: free <= 1 };
  }
  return { text: "", low: false };
}

export function showAgentBatteryPopover(anchor, detail) {
  document.querySelectorAll(".chat-agent-popover").forEach((el) => el.remove());
  const pop = document.createElement("div");
  pop.className = "chat-agent-popover";
  pop.dataset.testid = "maker-chat-agent-popover";
  const kind = detail.providerKind === "cloud" ? "cloud API" : "Ollama local";
  const executor = detail.executorLabel ? `<div>Executor: ${detail.executorLabel}</div>` : "";
  const nodeLine = detail.nodeLabel ? `<div>Node: ${detail.nodeLabel}</div>` : "";
  pop.innerHTML = `
    <strong>${detail.displayName}</strong>
    <div>Model: ${detail.modelId}</div>
    <div>Provider: ${detail.providerId} (${kind})</div>
    ${executor}
    ${nodeLine}
    <div class="chat-agent-popover__actions">
      <button type="button" class="btn btn--sm" data-action="hub">Open Model Hub</button>
      ${
        detail.providerKind !== "cloud"
          ? `<button type="button" class="btn btn--sm" data-action="pull">Pull ${detail.modelId}</button>`
          : ""
      }
    </div>`;
  pop.querySelector('[data-action="hub"]')?.addEventListener("click", () => {
    const section = detail.providerKind === "cloud" ? "api-connections" : "local";
    window.location.hash = `#/models?section=${section}`;
    pop.remove();
  });
  pop.querySelector('[data-action="pull"]')?.addEventListener("click", async () => {
    try {
      await apiJson("/platform/ollama/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: detail.modelId }),
      });
      toast(`Pull queued: ${detail.modelId}`, "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
    pop.remove();
  });
  const rect = anchor.getBoundingClientRect();
  pop.style.position = "fixed";
  pop.style.top = `${rect.bottom + 4}px`;
  pop.style.left = `${rect.left}px`;
  document.body.appendChild(pop);
  const close = (ev) => {
    if (!pop.contains(ev.target) && ev.target !== anchor) {
      pop.remove();
      document.removeEventListener("click", close);
    }
  };
  setTimeout(() => document.addEventListener("click", close), 0);
}

export function openModelSwapDialog({ agentRole, displayName, model, provider, providerKind }) {
  return new Promise((resolve) => {
    document.querySelectorAll(".chat-model-swap-dialog").forEach((el) => el.remove());
    const dlg = document.createElement("dialog");
    dlg.className = "chat-model-swap-dialog";
    dlg.dataset.testid = "maker-chat-model-swap-dialog";
    dlg.innerHTML = `
      <form method="dialog" class="chat-model-swap-form">
        <h4>Swap model — ${displayName}</h4>
        <label>Model id
          <input name="model_id" value="${model}" required data-testid="maker-chat-model-swap-input" />
        </label>
        <div class="actions">
          <button type="submit" value="ok">Swap</button>
          <button type="button" data-action="cancel">Cancel</button>
        </div>
      </form>`;
    const finish = (value) => {
      dlg.close();
      dlg.remove();
      resolve(value);
    };
    dlg.querySelector('[data-action="cancel"]')?.addEventListener("click", () => finish(null));
    dlg.querySelector("form")?.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const next = dlg.querySelector('input[name="model_id"]')?.value?.trim();
      if (!next || next === model) {
        finish(null);
        return;
      }
      finish({ agentRole, modelId: next, provider, providerKind });
    });
    document.body.appendChild(dlg);
    dlg.showModal();
    dlg.querySelector("input")?.focus();
  });
}
