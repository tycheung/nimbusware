import { apiJson, toast } from "../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../broker_miss.js"; // sak499-a
import { resolveCurrentUserId } from "./chat_collab_wiring.js";
import {
  nodeHeadroom,
  openModelSwapDialog,
  showAgentBatteryPopover,
} from "./chat_agent_popover_ui.js";

export { nodeHeadroom } from "./chat_agent_popover_ui.js";

async function fetchActiveClaims(runId) {
  const body = await apiJson(`/runs/${encodeURIComponent(runId)}/model-bindings/audit`).catch(
    (e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "model_bindings_audit",
      events: [],
    }),
  );
  if (isDomainPeelMiss(body)) {
    return { claims: {}, missBody: body };
  }
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
  return { claims, missBody: null };
}

async function postRoleClaim({ runId, sessionId, agentRole, binding }) {
  const body = {
    run_id: runId,
    agent_role: agentRole,
    provider_id: binding.provider_id || "ollama",
    model_id: binding.model_id || "default",
  };
  if (sessionId) {
    return apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/role-claims`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  return apiJson(`/runs/${encodeURIComponent(runId)}/role-claims`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function deleteRoleClaim({ runId, sessionId, agentRole }) {
  if (sessionId) {
    return apiJson(
      `/chat/sessions/${encodeURIComponent(sessionId)}/role-claims/${encodeURIComponent(agentRole)}?run_id=${encodeURIComponent(runId)}`,
      { method: "DELETE" },
    );
  }
  return apiJson(
    `/runs/${encodeURIComponent(runId)}/role-claims/${encodeURIComponent(agentRole)}`,
    { method: "DELETE" },
  );
}

export async function loadRunCardAgents(card, runId, { sessionId = null, computeNodes = [] } = {}) {
  const strip = card?.querySelector(".chat-run-card__agents");
  if (!strip) return;
  try {
    const [defaults, claimsResult, currentUserId] = await Promise.all([
      apiJson("/platform/model-bindings/defaults"),
      fetchActiveClaims(runId),
      resolveCurrentUserId(),
    ]);
    if (isDomainPeelMiss(defaults)) {
      strip.replaceChildren();
      const miss = document.createElement("span");
      miss.className = "muted";
      miss.dataset.testid = "maker-chat-agents-miss";
      miss.textContent =
        formatDomainMissMessage(defaults, "Agent bindings unavailable") || "Agent bindings unavailable";
      strip.appendChild(miss);
      toastIfMiss(defaults, toast, "Agent bindings unavailable");
      return;
    }
    const { claims, missBody: claimsMiss } = claimsResult;
    if (claimsMiss) {
      toastIfMiss(claimsMiss, toast, "Role claims audit unavailable");
    }
    const roles = (defaults.roles || []).slice(0, 6);
    strip.replaceChildren();
    const label = document.createElement("span");
    label.textContent = claimsMiss
      ? "Agents (claims unavailable): "
      : "Agents: ";
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
      const claimerId = String(claim?.claimer_user_id || "");
      const claimed = Boolean(claim);
      const claimedByMe = claimed && (!claimerId || claimerId === String(currentUserId || ""));
      const claimedByOther = claimed && claimerId && claimerId !== String(currentUserId || "");
      badge.textContent = `${row.display_name || agentRole} · ${model}${claimed ? " ★" : ""}`;
      badge.title = claimedByOther ? `Claimed by ${claimerId.slice(0, 8)}…` : "Swap model";
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
          const res = await apiJson(`/runs/${encodeURIComponent(runId)}/model-bindings/swap`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent_role: agentRole,
              provider_id: provider,
              provider_kind: binding.provider_kind || "local",
              model_id: swap.modelId,
            }),
          });
          if (toastIfMiss(res, toast, "Model swap unavailable")) return;
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
      claimBtn.textContent = claimedByMe ? "Release" : claimedByOther ? "Taken" : "Claim";
      claimBtn.disabled = claimedByOther;
      claimBtn.title = claimedByOther
        ? `Already claimed by ${claimerId.slice(0, 8)}…`
        : claimedByMe
          ? "Release this role"
          : "Claim this role for your node";
      claimBtn.onclick = async () => {
        if (claimedByOther) return;
        try {
          if (claimedByMe) {
            const res = await deleteRoleClaim({ runId, sessionId, agentRole });
            if (toastIfMiss(res, toast, "Role claim release unavailable")) return;
            toast(`Released ${agentRole}`, "success");
          } else {
            const hr = computeNodes.find((n) => nodeHeadroom(n).low);
            if (hr) {
              toast(`Low headroom on ${hr.display_name || hr.host_label || "a node"} — claim allowed`, "warn");
            }
            const res = await postRoleClaim({ runId, sessionId, agentRole, binding });
            if (toastIfMiss(res, toast, "Role claim unavailable")) return;
            toast(`Claimed ${agentRole}`, "success");
          }
          await loadRunCardAgents(card, runId, { sessionId, computeNodes });
        } catch (e) {
          const code = e?.body?.code || e?.code;
          if (code === "role_claim_conflict") {
            const who = e?.body?.details?.existing_claimer || "another operator";
            toast(`Role already claimed by ${String(who).slice(0, 8)}…`, "error");
          } else {
            toast(String(e.message || e), "error");
          }
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
  } catch (e) {
    strip.replaceChildren();
    const miss = document.createElement("span");
    miss.className = "muted";
    miss.dataset.testid = "maker-chat-agents-miss";
    miss.textContent =
      formatDomainMissMessage({ via: "broker_miss", error: String(e.message || e) }, "Agents unavailable") ||
      "Agents unavailable";
    strip.appendChild(miss);
    toast(String(e.message || e), "error");
  }
}
