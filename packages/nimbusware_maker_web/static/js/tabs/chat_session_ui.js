import { apiJson, toast } from "../api-client.js";

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

const TURN_ROLE_LABELS = {
  user: "You",
  participant: "Guest",
  classifier: "Classifier",
  work_type_switch: "Mode",
  run_status: "Run",
  theater: "Agent",
  system: "System",
};

export function workTypeLabel(value) {
  if (!value || value === "auto") return "Auto";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function turnRoleLabel(turn) {
  const role = turn.role || turn.kind || "system";
  return TURN_ROLE_LABELS[role] || "System";
}

export function renderTurnLine(thread, turn) {
  const role = turn.role || turn.kind || "system";
  const li = document.createElement("li");
  const cssRole = role === "participant" ? "participant" : role === "user" ? "user" : "system";
  li.className = `chat-thread-line chat-thread-line--${cssRole}`;
  if (role !== "user" && role !== "participant") li.classList.add(`chat-thread-line--${role}`);
  if (role === "participant") li.classList.add("chat-thread-line--participant");
  li.dataset.turnId = turn.turn_id || "";
  if (turn.turn_id) li.dataset.testid = `maker-chat-turn-${turn.turn_id}`;

  const label = document.createElement("strong");
  if (turn.payload?.kind === "discipline_route") {
    label.textContent = "Routed";
    li.classList.add("chat-thread-line--discipline-route");
    li.dataset.testid = "maker-chat-discipline-route";
  } else {
    label.textContent = turnRoleLabel(turn);
  }
  li.appendChild(label);
  li.appendChild(document.createTextNode(` ${turn.text || ""}`));

  if (turn.payload?.kind === "discipline_route" && turn.payload?.taxonomy_key) {
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = ` (${turn.payload.discipline || turn.payload.taxonomy_key})`;
    li.appendChild(meta);
  }

  if (role === "classifier" && turn.payload?.work_type) {
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = ` → ${workTypeLabel(turn.payload.work_type)}`;
    li.appendChild(meta);
  }

  if (role === "user" && turn.turn_id) {
    const actions = document.createElement("span");
    actions.className = "chat-turn-actions";
    const forkBtn = document.createElement("button");
    forkBtn.type = "button";
    forkBtn.className = "linkish";
    forkBtn.textContent = "Restore from here";
    forkBtn.dataset.testid = `maker-chat-fork-${turn.turn_id}`;
    forkBtn.addEventListener("click", () => li.dispatchEvent(new CustomEvent("chat-fork", { bubbles: true })));
    actions.appendChild(forkBtn);
    li.appendChild(actions);
  }
  thread.appendChild(li);
  thread.scrollTop = thread.scrollHeight;
}

export function renderMessagesFromSession(root, session) {
  if (session?.my_participant_role != null) {
    setCollabMyRole(session.my_participant_role);
  }
  renderParticipantStrip(root, session);
  applyComposerForRole(root);
  const thread = root.querySelector("#chat-thread");
  if (!thread) return;
  thread.replaceChildren();
  const turns = session.turns?.length ? session.turns : null;
  if (turns) {
    for (const turn of turns) {
      renderTurnLine(thread, turn);
    }
    return;
  }
  for (const msg of session.messages || []) {
    renderTurnLine(thread, {
      turn_id: msg.turn_id,
      role: msg.role === "user" ? "user" : msg.kind || "system",
      kind: msg.kind,
      text: msg.text,
      payload: msg.payload,
    });
  }
}

export function branchPanelCallbacks(root) {
  return { onSessionUpdated: (session) => renderMessagesFromSession(root, session) };
}

export function branchDepth(graph, turnId) {
  let depth = 0;
  let cur = turnId;
  while (cur) {
    const edge = graph.edges?.find((e) => e.to_turn_id === cur);
    if (!edge) break;
    depth += 1;
    cur = edge.from_turn_id;
  }
  return depth;
}

export function applySiblingBadges(root, graph) {
  const thread = root.querySelector("#chat-thread");
  if (!thread || !graph?.nodes) return;
  for (const node of graph.nodes) {
    const siblings = Number(node.sibling_count || 0);
    if (siblings < 1) continue;
    const line = thread.querySelector(`[data-turn-id="${node.turn_id}"]`);
    if (!line || line.querySelector(".chat-sibling-badge")) continue;
    const badge = document.createElement("span");
    badge.className = "chat-sibling-badge muted";
    badge.dataset.testid = `maker-chat-sibling-badge-${node.turn_id}`;
    badge.textContent = `${siblings + 1} branches`;
    line.appendChild(badge);
  }
}

function graphRoots(graph) {
  const childIds = new Set((graph.edges || []).map((e) => e.to_turn_id));
  return (graph.nodes || []).filter((n) => !childIds.has(n.turn_id));
}

function graphChildren(graph, turnId) {
  return (graph.edges || [])
    .filter((e) => e.from_turn_id === turnId)
    .map((e) => e.to_turn_id);
}

function nodeById(graph, turnId) {
  return (graph.nodes || []).find((n) => n.turn_id === turnId);
}

function leafTurnIds(graph) {
  return (graph.nodes || [])
    .filter((n) => !(graph.edges || []).some((e) => e.from_turn_id === n.turn_id))
    .map((n) => n.turn_id);
}

function renderTreeNode(
  root,
  graph,
  turnId,
  depth,
  activeLeafId,
  sessionId,
  list,
  { onSessionUpdated },
) {
  const node = nodeById(graph, turnId);
  if (!node) return;
  const li = document.createElement("li");
  li.className = "chat-branch-tree__node";
  li.style.paddingLeft = `${depth * 1.25}rem`;
  li.dataset.testid = `maker-chat-branch-tree-node-${turnId}`;
  const btn = document.createElement("button");
  btn.type = "button";
  const isLeaf = leafTurnIds(graph).includes(turnId);
  btn.className =
    turnId === activeLeafId || (isLeaf && turnId === activeLeafId)
      ? "linkish branch-active"
      : "linkish";
  btn.textContent = (node.text || node.turn_id).slice(0, 72);
  btn.dataset.testid = `maker-chat-branch-${turnId}`;
  if (isLeaf) {
    btn.addEventListener("click", async () => {
      const updated = await apiJson(
        `/chat/sessions/${encodeURIComponent(sessionId)}/active-leaf`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ leaf_turn_id: turnId }),
        },
      );
      onSessionUpdated?.(updated);
      await refreshBranchPanel(root, sessionId, { onSessionUpdated });
      toast("Switched branch", "success");
    });
  } else {
    btn.disabled = true;
    btn.title = "Select a leaf branch to switch active path";
  }
  li.appendChild(btn);
  if (Number(node.sibling_count || 0) > 0) {
    const badge = document.createElement("span");
    badge.className = "chat-sibling-badge muted";
    badge.textContent = `${Number(node.sibling_count) + 1} branches`;
    li.appendChild(badge);
  }
  list.appendChild(li);
  const childIds = graphChildren(graph, turnId);
  for (const childId of childIds) {
    renderTreeNode(root, graph, childId, depth + 1, activeLeafId, sessionId, list, {
      onSessionUpdated,
    });
  }
}

export async function refreshBranchPanel(root, sessionId, { onSessionUpdated } = {}) {
  const panel = root.querySelector("#chat-branch-panel");
  if (!panel || !sessionId) return;
  try {
    const graph = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/graph`);
    panel.replaceChildren();
    if (!graph.nodes?.length) {
      applySiblingBadges(root, graph);
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    const title = document.createElement("h4");
    title.textContent = "Conversation branches";
    panel.appendChild(title);
    const list = document.createElement("ul");
    list.className = "chat-branch-tree";
    list.dataset.testid = "maker-chat-branch-tree";
    const activeLeafId =
      graph.active_leaf_turn_id ||
      leafTurnIds(graph)[leafTurnIds(graph).length - 1] ||
      "";
    for (const rootNode of graphRoots(graph)) {
      renderTreeNode(root, graph, rootNode.turn_id, 0, activeLeafId, sessionId, list, {
        onSessionUpdated,
      });
    }
    panel.appendChild(list);
    applySiblingBadges(root, graph);
  } catch {
    panel.classList.add("hidden");
  }
}
