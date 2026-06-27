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
    const disciplineMark = p.user_discipline ? ` · ${p.user_discipline}` : "";
    const expertiseMark =
      Array.isArray(p.expertise_bullets) && p.expertise_bullets.length
        ? ` · ${p.expertise_bullets.slice(0, 2).join(", ")}`
        : "";
    const profiles = [];
    if (p.autopilot_profile_id) profiles.push(`trust:${p.autopilot_profile_id}`);
    if (p.enforcement_profile_id) profiles.push(`enforce:${p.enforcement_profile_id}`);
    const profileMark = profiles.length ? ` [${profiles.join(", ")}]` : "";
    return `${name} · ${role}${disciplineMark}${expertiseMark}${hostMark}${profileMark}`;
  });
  strip.replaceChildren();
  const text = document.createElement("span");
  text.className = "chat-participant-strip-text";
  text.textContent = `Participants: ${bits.join(" · ")}`;
  strip.appendChild(text);
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
    panel.hidden = false;
    list.replaceChildren();
    if (!nodes.length) {
      const empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = "No compute nodes registered for this session.";
      list.appendChild(empty);
    }
    for (const node of nodes) {
      const li = document.createElement("li");
      const label = node.display_name || node.host_label || node.node_id;
      const policy = node.share_policy || "off";
      const delegate = node.allow_host_resource_management ? " · host may configure" : "";
      li.textContent = `${label} · ${node.status || "unknown"} · ${policy}${delegate}`;
      list.appendChild(li);
    }
    let delegateRow = panel.querySelector("[data-testid='maker-chat-delegate-control']");
    const role = getCollabMyRole();
    if (role === "session_write" || role === "session_admin") {
      if (!delegateRow) {
        delegateRow = document.createElement("label");
        delegateRow.className = "chat-delegate-control";
        delegateRow.dataset.testid = "maker-chat-delegate-control";
        delegateRow.innerHTML = `
          <input type="checkbox" id="chat-delegate-control" />
          Allow host to manage my compute bindings for this session
        `;
        panel.appendChild(delegateRow);
        delegateRow.querySelector("input")?.addEventListener("change", async (ev) => {
          const enabled = ev.target.checked;
          try {
            await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/compute/delegate-control`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ allow_host_resource_management: enabled }),
            });
          } catch {
            ev.target.checked = !enabled;
          }
        });
      }
      const mine = nodes.find((n) => n.allow_host_resource_management);
      const box = delegateRow.querySelector("input");
      if (box) box.checked = Boolean(mine?.allow_host_resource_management);
    } else {
      delegateRow?.remove();
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
