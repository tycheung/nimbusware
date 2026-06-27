import {
  applyComposerForRole,
  renderParticipantStrip,
  setCollabMyRole,
} from "./chat_session_ui.js";

const TURN_ROLE_LABELS = {
  user: "You",
  participant: "Guest",
  classifier: "Classifier",
  work_type_switch: "Mode",
  run_status: "Run",
  theater: "Agent",
  system: "System",
};
function workTypeLabel(value) {
  if (!value || value === "auto") return "Auto";
  return value.charAt(0).toUpperCase() + value.slice(1);
}
function turnRoleLabel(turn) {
  const role = turn.role || turn.kind || "system";
  return TURN_ROLE_LABELS[role] || "System";
}

function renderTurnLine(thread, turn) {
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

function renderMessagesFromSession(root, session) {
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

function branchPanelCallbacks(root) {
  return { onSessionUpdated: (session) => renderMessagesFromSession(root, session) };
}

export { branchPanelCallbacks, renderMessagesFromSession, renderTurnLine, workTypeLabel };
