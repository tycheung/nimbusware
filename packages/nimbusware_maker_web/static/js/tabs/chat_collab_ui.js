import { apiJson } from "../api-client.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { closeInviteModal, openInviteModal } from "./chat_invite_modal_ui.js";
import { getCollabMyRole } from "./chat_session_ui.js";

export { closeInviteModal } from "./chat_invite_modal_ui.js";

let sessionStreamHandle = null;

export function mountInviteButton(root, sessionId) {
  const role = getCollabMyRole();
  if (role !== "session_admin") return;
  let btn = root.querySelector("[data-testid='maker-chat-invite-btn']");
  if (!btn) {
    const strip = root.querySelector("[data-testid='maker-chat-participants']");
    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "linkish chat-invite-btn";
    btn.dataset.testid = "maker-chat-invite-btn";
    btn.textContent = "Invite…";
    strip?.appendChild(btn);
  }
  btn.onclick = () => openInviteModal(root, sessionId);
}

export function mountCommentaryComposer(root, sessionId, onTurn) {
  const role = getCollabMyRole();
  if (role === "session_read" || !sessionId) return;
  let box = root.querySelector("[data-testid='maker-chat-commentary']");
  if (!box) {
    box = document.createElement("form");
    box.className = "chat-commentary panel";
    box.dataset.testid = "maker-chat-commentary";
    box.innerHTML = `
      <label>Commentary
        <textarea rows="2" placeholder="Comment for the group…" data-testid="maker-chat-commentary-input"></textarea>
      </label>
      <button type="submit" class="secondary">Post comment</button>
    `;
    const thread = root.querySelector("#chat-thread");
    thread?.insertAdjacentElement("beforebegin", box);
  }
  box.onsubmit = async (ev) => {
    ev.preventDefault();
    const input = box.querySelector("[data-testid='maker-chat-commentary-input']");
    const text = input?.value?.trim() || "";
    if (!text) return;
    try {
      const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/commentary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      input.value = "";
      onTurn?.(body.turn);
    } catch (e) {
      console.error(e);
    }
  };
}

export function bindSessionStream(root, sessionId, { onSession } = {}) {
  sessionStreamHandle?.close();
  sessionStreamHandle = null;
  if (!sessionId) return null;
  sessionStreamHandle = openSseStream(`/chat/sessions/${encodeURIComponent(sessionId)}/stream`, {
    onEvent: {
      session: (ev) => {
        const data = parseSseJson(ev);
        if (data) onSession?.(data);
      },
    },
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data?.theater_lines) onSession?.(data);
    },
  });
  return sessionStreamHandle;
}

export function unbindSessionStream() {
  sessionStreamHandle?.close();
  sessionStreamHandle = null;
}
