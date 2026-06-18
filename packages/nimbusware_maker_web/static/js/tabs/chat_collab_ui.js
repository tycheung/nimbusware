import { apiJson } from "../api-client.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { getCollabMyRole } from "./chat_session_ui.js";

let sessionStreamHandle = null;

export function closeInviteModal() {
  document.querySelector("[data-testid='maker-chat-invite-modal']")?.remove();
}

function copyText(text) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  ta.remove();
  return Promise.resolve();
}

async function createInviteLink(sessionId, role) {
  const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/invites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, expires_hours: 24 }),
  });
  const origin = window.location.origin;
  return `${origin}${body.join_url}`;
}

async function searchEnterpriseUsers(query) {
  try {
    const body = await apiJson(`/enterprise/users?q=${encodeURIComponent(query)}`);
    return body.users || [];
  } catch {
    return [];
  }
}

async function listGroups() {
  try {
    const body = await apiJson("/chat/groups");
    return body.groups || [];
  } catch {
    return [];
  }
}

export function openInviteModal(root, sessionId) {
  if (!sessionId) return;
  closeInviteModal();
  const overlay = document.createElement("div");
  overlay.className = "chat-modal-overlay";
  overlay.dataset.testid = "maker-chat-invite-modal";
  overlay.innerHTML = `
    <div class="chat-modal panel" role="dialog" aria-labelledby="chat-invite-title">
      <h3 id="chat-invite-title">Invite to session</h3>
      <div class="chat-invite-tabs" role="tablist">
        <button type="button" class="chat-invite-tab chat-invite-tab--active" data-tab="link">Link</button>
        <button type="button" class="chat-invite-tab" data-tab="directory">Directory</button>
        <button type="button" class="chat-invite-tab" data-tab="group">Group</button>
      </div>
      <div class="chat-invite-panel" data-panel="link">
        <label>Role
          <select id="chat-invite-role-link">
            <option value="session_read">Read (watch)</option>
            <option value="session_write">Write</option>
            <option value="session_admin">Admin</option>
          </select>
        </label>
        <button type="button" id="chat-invite-copy-link" data-testid="maker-chat-invite-copy-link">Copy invite link</button>
        <p id="chat-invite-link-status" class="muted"></p>
      </div>
      <div class="chat-invite-panel hidden" data-panel="directory">
        <label>Search users
          <input type="search" id="chat-invite-user-search" placeholder="name or username" />
        </label>
        <ul id="chat-invite-user-results" class="chat-invite-results"></ul>
      </div>
      <div class="chat-invite-panel hidden" data-panel="group">
        <label>Group
          <select id="chat-invite-group-select"></select>
        </label>
        <label>Grant role
          <select id="chat-invite-group-role">
            <option value="session_read">Read</option>
            <option value="session_write">Write</option>
          </select>
        </label>
        <button type="button" id="chat-invite-group-grant">Grant folder access via group</button>
        <p class="muted">Adds a group-scoped library grant for this session's folder.</p>
      </div>
      <div class="actions">
        <button type="button" class="linkish" id="chat-invite-close">Close</button>
      </div>
    </div>
  `;
  root.appendChild(overlay);

  const showTab = (name) => {
    overlay.querySelectorAll(".chat-invite-tab").forEach((btn) => {
      btn.classList.toggle("chat-invite-tab--active", btn.dataset.tab === name);
    });
    overlay.querySelectorAll(".chat-invite-panel").forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.panel !== name);
    });
  };

  overlay.querySelectorAll(".chat-invite-tab").forEach((btn) => {
    btn.addEventListener("click", () => showTab(btn.dataset.tab || "link"));
  });
  overlay.querySelector("#chat-invite-close")?.addEventListener("click", closeInviteModal);
  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay) closeInviteModal();
  });

  overlay.querySelector("#chat-invite-copy-link")?.addEventListener("click", async () => {
    const role = overlay.querySelector("#chat-invite-role-link")?.value || "session_read";
    const status = overlay.querySelector("#chat-invite-link-status");
    try {
      const url = await createInviteLink(sessionId, role);
      await copyText(url);
      if (status) status.textContent = "Invite link copied.";
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
    }
  });

  const userSearch = overlay.querySelector("#chat-invite-user-search");
  const userResults = overlay.querySelector("#chat-invite-user-results");
  userSearch?.addEventListener("input", async () => {
    const q = userSearch.value.trim();
    if (!userResults || q.length < 2) {
      userResults?.replaceChildren();
      return;
    }
    const users = await searchEnterpriseUsers(q);
    userResults.replaceChildren();
    for (const u of users) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `${u.display_name || u.username} · invite as Write`;
      btn.addEventListener("click", async () => {
        try {
          await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/participants`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: u.user_id, role: "session_write" }),
          });
          btn.textContent = "Added";
          btn.disabled = true;
        } catch (e) {
          btn.textContent = String(e.message || e);
        }
      });
      li.appendChild(btn);
      userResults.appendChild(li);
    }
  });

  listGroups().then((groups) => {
    const sel = overlay.querySelector("#chat-invite-group-select");
    if (!sel) return;
    for (const g of groups) {
      const opt = document.createElement("option");
      opt.value = g.group_id;
      opt.textContent = g.name;
      sel.appendChild(opt);
    }
  });

  overlay.querySelector("#chat-invite-group-grant")?.addEventListener("click", async () => {
    const groupId = overlay.querySelector("#chat-invite-group-select")?.value;
    const role = overlay.querySelector("#chat-invite-group-role")?.value || "session_read";
    if (!groupId) return;
    try {
      await apiJson("/chat/grants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          grantee_type: "group",
          grantee_group_id: groupId,
          scope_type: "session",
          session_id: sessionId,
          participant_role: role,
        }),
      });
      const status = overlay.querySelector("#chat-invite-link-status");
      if (status) status.textContent = "Group grant created.";
    } catch (e) {
      const status = overlay.querySelector("#chat-invite-link-status");
      if (status) status.textContent = String(e.message || e);
    }
  });
}

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
