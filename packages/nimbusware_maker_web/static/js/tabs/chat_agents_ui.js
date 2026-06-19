import { apiJson, toast } from "../api-client.js";

function nodeHeadroom(node) {
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

function openModelSwapDialog({ agentRole, displayName, model, provider, providerKind }) {
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

async function fetchActiveClaims(runId) {
  try {
    const body = await apiJson(`/runs/${encodeURIComponent(runId)}/model-bindings/audit`);
    const claims = {};
    for (const ev of body.events || []) {
      const p = ev.payload || {};
      const role = p.agent_role;
      if (!role) continue;
      if (ev.event_type === "workload.role_claimed") {
        claims[role] = p;
      } else if (ev.event_type === "workload.role_released") {
        delete claims[role];
      }
    }
    return claims;
  } catch {
    return {};
  }
}

async function postRoleClaim({ runId, sessionId, agentRole, binding }) {
  const body = {
    run_id: runId,
    agent_role: agentRole,
    provider_id: binding.provider_id || "ollama",
    model_id: binding.model_id || "default",
  };
  if (sessionId) {
    await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/role-claims`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } else {
    await apiJson(`/runs/${encodeURIComponent(runId)}/role-claims`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
}

async function deleteRoleClaim({ runId, sessionId, agentRole }) {
  if (sessionId) {
    await apiJson(
      `/chat/sessions/${encodeURIComponent(sessionId)}/role-claims/${encodeURIComponent(agentRole)}?run_id=${encodeURIComponent(runId)}`,
      { method: "DELETE" },
    );
  } else {
    await apiJson(
      `/runs/${encodeURIComponent(runId)}/role-claims/${encodeURIComponent(agentRole)}`,
      { method: "DELETE" },
    );
  }
}

export async function loadRunCardAgents(card, runId, { sessionId = null, computeNodes = [] } = {}) {
  const strip = card?.querySelector(".chat-run-card__agents");
  if (!strip) return;
  try {
    const [defaults, claims] = await Promise.all([
      apiJson("/platform/model-bindings/defaults"),
      fetchActiveClaims(runId),
    ]);
    const roles = (defaults.roles || []).slice(0, 6);
    strip.replaceChildren();
    const label = document.createElement("span");
    label.textContent = "Agents: ";
    strip.appendChild(label);
    for (const row of roles) {
      const binding = row.binding || {};
      const agentRole = row.agent_role;
      const claim = claims[agentRole];
      const wrap = document.createElement("span");
      wrap.className = "chat-agent-badge-wrap";
      const badge = document.createElement("button");
      badge.type = "button";
      badge.className = "chat-agent-badge";
      badge.dataset.testid = `maker-chat-agent-${agentRole}`;
      const model = binding.model_id || "default";
      const provider = binding.provider_id || "ollama";
      const claimed = Boolean(claim);
      badge.textContent = `${row.display_name || agentRole} · ${model}${claimed ? " ★" : ""}`;
      badge.title = "Swap model";
      badge.onclick = async () => {
        const swap = await openModelSwapDialog({
          agentRole,
          displayName: row.display_name || agentRole,
          model,
          provider,
          providerKind: binding.provider_kind || "local",
        });
        if (!swap) return;
        try {
          await apiJson(`/runs/${encodeURIComponent(runId)}/model-bindings/swap`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent_role: agentRole,
              provider_id: provider,
              provider_kind: binding.provider_kind || "local",
              model_id: swap.modelId,
            }),
          });
          toast(`Swapped ${agentRole} to ${swap.modelId}`, "success");
          await loadRunCardAgents(card, runId, { sessionId, computeNodes });
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      };
      const claimBtn = document.createElement("button");
      claimBtn.type = "button";
      claimBtn.className = "chat-agent-claim linkish";
      claimBtn.dataset.testid = `maker-chat-agent-claim-${agentRole}`;
      claimBtn.textContent = claimed ? "Release" : "Claim";
      claimBtn.onclick = async () => {
        try {
          if (claimed) {
            await deleteRoleClaim({ runId, sessionId, agentRole });
            toast(`Released ${agentRole}`, "success");
          } else {
            const hr = computeNodes.find((n) => nodeHeadroom(n).low);
            if (hr) {
              toast(`Low headroom on ${hr.display_name || hr.host_label || "a node"} — claim allowed`, "warn");
            }
            await postRoleClaim({ runId, sessionId, agentRole, binding });
            toast(`Claimed ${agentRole}`, "success");
          }
          await loadRunCardAgents(card, runId, { sessionId, computeNodes });
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      };
      const info = document.createElement("button");
      info.type = "button";
      info.className = "chat-agent-info";
      info.textContent = "ⓘ";
      info.title = "Battery details";
      info.dataset.testid = `maker-chat-agent-info-${agentRole}`;
      info.onclick = (ev) => {
        ev.stopPropagation();
        const claimer = claim?.claimer_user_id || "";
        const node = computeNodes.find((n) => n.user_id === claimer);
        showAgentBatteryPopover(info, {
          agentRole,
          displayName: row.display_name || agentRole,
          modelId: model,
          providerId: provider,
          providerKind: binding.provider_kind || "local",
          executorLabel: claimer ? `@${claimer.slice(0, 8)}` : "host",
          nodeLabel: node?.display_name || node?.host_label || "",
        });
      };
      wrap.append(badge, claimBtn, info);
      strip.appendChild(wrap);
    }
  } catch {
    strip.textContent = "Agents: —";
  }
}

export { nodeHeadroom };
