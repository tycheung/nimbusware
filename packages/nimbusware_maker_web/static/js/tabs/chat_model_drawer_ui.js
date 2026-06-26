import { apiJson, toast } from "../api-client.js";
import { getCollabMyRole } from "./chat_session_ui.js";

function canEditBindings(collabRole) {
  return collabRole === "session_admin" || collabRole === "session_write";
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
  const [defaults, sessionBindings, rolesBody] = await Promise.all([
    apiJson("/platform/model-bindings/defaults").catch(() => ({ roles: [], defaults: { roles: {} } })),
    apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/participant-bindings`),
    apiJson("/platform/model-bindings/roles").catch(() => ({ roles: [] })),
  ]);
  const catalog = rolesBody.roles?.length ? rolesBody.roles : defaults.roles || [];
  return { catalog, sessionRoles: sessionBindings.roles || {}, providers: defaults.providers || [] };
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
    const { catalog, sessionRoles, providers } = await loadDrawerData(sessionId);
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = "<thead><tr><th>Role</th><th>Provider</th><th>Model</th><th></th></tr></thead>";
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
      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "secondary";
      saveBtn.textContent = "Save";
      saveBtn.addEventListener("click", async () => {
        try {
          await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/participant-bindings`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent_role: role,
              provider_kind: binding.provider_kind || "cloud",
              provider_id: providerSelect.value,
              model_id: modelInput.value.trim(),
              connection_id: binding.connection_id || null,
            }),
          });
          toast(`Saved ${role}`, "success");
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      tr.appendChild(document.createElement("td")).textContent = row.display_name || role;
      tr.appendChild(document.createElement("td")).appendChild(providerSelect);
      tr.appendChild(document.createElement("td")).appendChild(modelInput);
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
