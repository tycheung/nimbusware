import { apiJson } from "../api-client.js";
import { nodeHeadroom } from "./chat_agents_ui.js";

function canOpenDrawer(collabRole) {
  return collabRole === "session_admin" || collabRole === "session_write";
}

function renderNodeRow(node) {
  const li = document.createElement("li");
  li.className = "accessible-compute-node";
  const label = node.display_name || node.host_label || node.node_id?.slice(0, 8) || "node";
  const hr = nodeHeadroom(node);
  const headroom = hr.text ? ` · ${hr.text}${hr.low ? " ⚠ low headroom" : ""}` : "";
  const delegate = node.allow_host_resource_management ? " · delegate OK" : "";
  const policy = node.share_policy && node.share_policy !== "off" ? ` · ${node.share_policy}` : "";
  li.textContent = `${label} · ${node.status || "unknown"}${policy}${headroom}${delegate}`;
  if (hr.low) li.classList.add("accessible-compute-node--low-headroom");
  return li;
}

export function mountAccessibleComputeTrigger(root, { sessionId, collabRole, onOpen }) {
  const host = root.querySelector(".chat-main");
  if (!host || !sessionId) return;
  let btn = root.querySelector('[data-testid="maker-accessible-compute-trigger"]');
  if (!canOpenDrawer(collabRole)) {
    btn?.remove();
    return;
  }
  if (!btn) {
    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--sm accessible-compute-trigger";
    btn.dataset.testid = "maker-accessible-compute-trigger";
    btn.textContent = "Accessible compute";
    host.insertBefore(btn, host.firstChild);
    btn.addEventListener("click", () => onOpen?.());
  }
}

export async function openAccessibleComputeDrawer(root, sessionId) {
  document.querySelectorAll(".accessible-compute-drawer").forEach((el) => el.remove());
  const drawer = document.createElement("aside");
  drawer.className = "accessible-compute-drawer panel";
  drawer.dataset.testid = "maker-accessible-compute";
  drawer.innerHTML = `
    <header class="accessible-compute-drawer__header">
      <h4>Accessible compute</h4>
      <button type="button" class="linkish" data-action="close">Close</button>
    </header>
    <p class="muted accessible-compute-drawer__hint">
      Machines you may route work to (metadata only — no API keys).
    </p>
    <ul class="accessible-compute-drawer__list"></ul>`;
  const list = drawer.querySelector(".accessible-compute-drawer__list");
  drawer.querySelector('[data-action="close"]')?.addEventListener("click", () => drawer.remove());
  root.appendChild(drawer);
  try {
    const body = await apiJson(`/compute/nodes?session_id=${encodeURIComponent(sessionId)}`);
    const nodes = (body.nodes || []).filter(
      (n) => n.allow_host_resource_management || (n.share_policy && n.share_policy !== "off"),
    );
    list.replaceChildren();
    if (!nodes.length) {
      const empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = "No delegate-capable compute nodes for this session.";
      list.appendChild(empty);
    } else {
      for (const node of nodes) list.appendChild(renderNodeRow(node));
    }
  } catch {
    list.replaceChildren();
    const err = document.createElement("li");
    err.className = "muted";
    err.textContent = "Could not load compute nodes.";
    list.appendChild(err);
  }
  return drawer;
}

export async function refreshAccessibleComputeTrigger(root, sessionId, collabRole) {
  mountAccessibleComputeTrigger(root, {
    sessionId,
    collabRole,
    onOpen: () => openAccessibleComputeDrawer(root, sessionId),
  });
}
