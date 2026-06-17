import { apiJson } from "../api-client.js";

let collabMyRole = null;

export function getCollabMyRole() {
  return collabMyRole;
}

export function setCollabMyRole(role) {
  collabMyRole = role;
}

export function renderParticipantStrip(root, session) {
  let strip = root.querySelector("[data-testid='maker-chat-participants']");
  if (!strip) {
    strip = document.createElement("div");
    strip.className = "chat-participant-strip muted";
    strip.dataset.testid = "maker-chat-participants";
    const main = root.querySelector(".chat-main");
    const form = root.querySelector("#chat-form");
    if (main && form) {
      main.insertBefore(strip, form);
    } else {
      root.prepend(strip);
    }
  }
  const participants = session?.participants || [];
  if (!participants.length) {
    strip.textContent = "";
    strip.classList.add("hidden");
    return;
  }
  strip.classList.remove("hidden");
  const bits = participants.map((p) => {
    const name = p.display_name || p.username || p.user_id?.slice(0, 8) || "user";
    const role = String(p.role || "session_read").replace("session_", "");
    const hostMark = session?.host_user_id && p.user_id === session.host_user_id ? " ★" : "";
    return `${name} · ${role}${hostMark}`;
  });
  strip.textContent = `Participants: ${bits.join(" · ")}`;
}

export function applyComposerForRole(root) {
  const form = root.querySelector("#chat-form");
  const readOnly = collabMyRole === "session_read";
  if (form) form.classList.toggle("hidden", readOnly);
  const inj = root.querySelector("[data-testid='maker-chat-interjection-ribbon']");
  if (inj) inj.classList.toggle("hidden", readOnly);
  let banner = root.querySelector("[data-testid='maker-chat-readonly-banner']");
  if (readOnly) {
    if (!banner) {
      banner = document.createElement("p");
      banner.className = "muted chat-readonly-banner";
      banner.dataset.testid = "maker-chat-readonly-banner";
      banner.textContent =
        "You're watching as read-only. Ask the host for Write access to comment.";
      form?.insertAdjacentElement("beforebegin", banner);
    }
  } else {
    banner?.remove();
  }
}

export async function refreshComputeNodes(root, sessionId) {
  const panel = root.querySelector("#chat-compute-nodes");
  const list = root.querySelector("#chat-compute-nodes-list");
  if (!panel || !list || !sessionId) return;
  try {
    const body = await apiJson(
      `/compute/nodes?session_id=${encodeURIComponent(sessionId)}`,
    );
    const nodes = body.nodes || [];
    if (!nodes.length) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    list.replaceChildren();
    for (const node of nodes) {
      const li = document.createElement("li");
      const label = node.display_name || node.host_label || node.node_id;
      li.textContent = `${label} · ${node.status || "unknown"}`;
      list.appendChild(li);
    }
  } catch {
    panel.hidden = true;
  }
}

export async function refreshSessionSidebar(root, projectId, activeSessionId, onSelect) {
  const list = root.querySelector("#chat-session-list");
  if (!list || !projectId) return;
  try {
    const sessions = await apiJson(`/chat/sessions?project_id=${encodeURIComponent(projectId)}`);
    list.replaceChildren();
    const sorted = [...(sessions || [])].sort(
      (a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")),
    );
    for (const session of sorted) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        session.session_id === activeSessionId
          ? "chat-session-item chat-session-item--active"
          : "chat-session-item";
      btn.dataset.testid = `maker-chat-session-${session.session_id}`;
      const title = session.title || `Session ${String(session.session_id).slice(0, 8)}`;
      btn.textContent = title;
      btn.title = session.updated_at || "";
      btn.addEventListener("click", () => onSelect(session.session_id));
      li.appendChild(btn);
      list.appendChild(li);
    }
  } catch {
    list.replaceChildren();
    const err = document.createElement("li");
    err.className = "muted";
    err.textContent = "Sessions unavailable";
    list.appendChild(err);
  }
}
