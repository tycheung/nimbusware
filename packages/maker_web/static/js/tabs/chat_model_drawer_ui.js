import { apiJson, toast } from "../api-client.js";
import {
  formatDomainMissMessage,
  isDomainPeelMiss,
  toastIfMiss,
  toastIfMisses,
} from "../broker_miss.js"; // sak498-f
import { getCollabMyRole } from "./chat_session_ui.js";

function canEditBindings(collabRole) {
  return collabRole === "session_admin" || collabRole === "session_write";
}

function providerKindFor(providers, providerId) {
  const match = (providers || []).find(
    (p) => String(p.id || p.provider_id || "") === String(providerId),
  );
  const kind = String(match?.kind || match?.provider_kind || "").toLowerCase();
  if (kind === "local" || kind === "ollama") return "local";
  if (kind) return kind;
  return providerId === "ollama" ? "local" : "cloud";
}

export function mountCollabModelDrawerTrigger(root, sessionId) {
  const role = getCollabMyRole();
  if (!canEditBindings(role) || !sessionId) return;
  const strip = root.querySelector("[data-testid='maker-chat-participants']");
  if (!strip || strip.querySelector("[data-testid='maker-chat-model-drawer-btn']")) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "linkish";
  btn.dataset.testid = "maker-chat-model-drawer-btn";
  btn.textContent = "Session models";
  btn.title = "Pick provider and model per role for this session";
  btn.addEventListener("click", () => openCollabModelDrawer(root, sessionId));
  strip.appendChild(btn);
}

async function loadDrawerData(sessionId) {
  // sak496-j: partial multi-fetch misses aggregate to one toast + combined banner.
  let defaults;
  let sessionBindings;
  let rolesBody;
  let connections;
  try {
    defaults = await apiJson("/platform/model-bindings/defaults");
  } catch (e) {
    defaults = {
      via: "broker_miss",
      error: String(e.message || e),
      feature: "platform_model_bindings_defaults",
    };
  }
  try {
    sessionBindings = await apiJson(
      `/chat/sessions/${encodeURIComponent(sessionId)}/participant-bindings`,
    );
  } catch (e) {
    sessionBindings = {
      via: "broker_miss",
      error: String(e.message || e),
      feature: "participant_bindings",
    };
  }
  try {
    rolesBody = await apiJson("/platform/model-bindings/roles");
  } catch (e) {
    rolesBody = {
      via: "broker_miss",
      error: String(e.message || e),
      feature: "platform_model_bindings_roles",
      roles: [],
    };
  }
  try {
    connections = await apiJson("/platform/provider-connections");
  } catch (e) {
    connections = {
      via: "broker_miss",
      error: String(e.message || e),
      feature: "provider_connections",
      connections: [],
    };
  }
  const misses = [defaults, sessionBindings, rolesBody, connections].filter((body) =>
    isDomainPeelMiss(body),
  );
  toastIfMisses(misses, toast, "Session models unavailable");
  const missBanner =
    misses
      .map((body) => formatDomainMissMessage(body, "Session models unavailable"))
      .find(Boolean) || null;
  return {
    catalog: isDomainPeelMiss(defaults)
      ? []
      : !isDomainPeelMiss(rolesBody) && rolesBody.roles?.length
        ? rolesBody.roles
        : defaults.roles || [],
    sessionRoles: isDomainPeelMiss(sessionBindings) ? {} : sessionBindings.roles || {},
    providers: isDomainPeelMiss(defaults) ? [] : defaults.providers || [],
    connections: isDomainPeelMiss(connections)
      ? []
      : connections.connections || connections.items || [],
    missBanner:
      missBanner ||
      (isDomainPeelMiss(defaults) &&
        formatDomainMissMessage(defaults, "Model bindings unavailable")) ||
      (isDomainPeelMiss(sessionBindings) &&
        formatDomainMissMessage(sessionBindings, "Participant bindings unavailable")) ||
      null,
  };
}

export async function openCollabModelDrawer(root, sessionId) {
  document.querySelectorAll(".collab-model-drawer").forEach((el) => el.remove());
  const drawer = document.createElement("aside");
  drawer.className = "collab-model-drawer panel";
  drawer.dataset.testid = "maker-chat-collab-models-drawer";
  drawer.innerHTML = `
    <header class="collab-model-drawer__header">
      <h4>Session models</h4>
      <button type="button" class="linkish" data-action="close">Close</button>
    </header>
    <p class="muted">Bindings apply to your participant vault for this session.</p>
    <div class="collab-model-drawer__table" data-testid="maker-chat-model-drawer-table"></div>`;
  drawer.querySelector('[data-action="close"]')?.addEventListener("click", () => drawer.remove());
  root.appendChild(drawer);

  const host = drawer.querySelector("[data-testid='maker-chat-model-drawer-table']");
  try {
    const { catalog, sessionRoles, providers, connections, missBanner } =
      await loadDrawerData(sessionId);
    if (missBanner) {
      const banner = document.createElement("p");
      banner.className = "muted";
      banner.dataset.testid = "maker-chat-model-drawer-miss";
      banner.textContent = missBanner;
      host.replaceChildren(banner);
      return drawer;
    }
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML =
      "<thead><tr><th>Role</th><th>Provider</th><th>Model</th><th>Connection</th><th></th></tr></thead>";
    const tbody = document.createElement("tbody");
    for (const row of catalog) {
      const role = row.agent_role || "";
      const binding = sessionRoles[role] || row.binding || {};
      const tr = document.createElement("tr");
      tr.dataset.testid = `maker-chat-model-row-${role}`;
      const providerSelect = document.createElement("select");
      providerSelect.dataset.role = role;
      for (const p of providers) {
        const opt = document.createElement("option");
        opt.value = String(p.id || p.provider_id || "");
        opt.textContent = String(p.label || p.id || "");
        if (opt.value === (binding.provider_id || "ollama")) opt.selected = true;
        providerSelect.appendChild(opt);
      }
      const modelInput = document.createElement("input");
      modelInput.type = "text";
      modelInput.value = String(binding.model_id || "");
      modelInput.dataset.role = role;
      const connectionSelect = document.createElement("select");
      connectionSelect.dataset.role = role;
      const noneOpt = document.createElement("option");
      noneOpt.value = "";
      noneOpt.textContent = "(default)";
      connectionSelect.appendChild(noneOpt);
      for (const c of connections) {
        const opt = document.createElement("option");
        opt.value = String(c.connection_id || c.id || "");
        opt.textContent = String(c.label || c.name || opt.value);
        if (opt.value && opt.value === String(binding.connection_id || "")) opt.selected = true;
        connectionSelect.appendChild(opt);
      }
      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "secondary";
      saveBtn.textContent = "Save";
      saveBtn.addEventListener("click", async () => {
        try {
          const providerId = providerSelect.value;
          const connId = connectionSelect.value.trim();
          const res = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/participant-bindings`,
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                agent_role: role,
                provider_kind: providerKindFor(providers, providerId),
                provider_id: providerId,
                model_id: modelInput.value.trim(),
                connection_id: connId || null,
              }),
            },
          );
          if (toastIfMiss(res, toast, "Participant binding save unavailable")) return; // sak496-j
          toast(`Saved ${role}`, "success");
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      tr.appendChild(document.createElement("td")).textContent = row.display_name || role;
      tr.appendChild(document.createElement("td")).appendChild(providerSelect);
      tr.appendChild(document.createElement("td")).appendChild(modelInput);
      tr.appendChild(document.createElement("td")).appendChild(connectionSelect);
      tr.appendChild(document.createElement("td")).appendChild(saveBtn);
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    host?.appendChild(table);
  } catch (e) {
    host.textContent = String(e.message || e);
  }
  return drawer;
}
