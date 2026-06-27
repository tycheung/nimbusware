import { apiJson } from "../api-client.js";

function joinTokenFromHash() {
  const path = (window.location.hash.replace(/^#/, "").split("?")[0] || "").trim();
  const match = path.match(/^\/chat\/join\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function ensureSignedIn(username, password, displayName, mode) {
  const path = mode === "signup" ? "/auth/signup" : "/auth/signin";
  const body =
    mode === "signup"
      ? { username, password, display_name: displayName || username }
      : { username, password };
  return apiJson(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function loadDisciplineOptions() {
  try {
    const body = await apiJson("/platform/collab-disciplines");
    return body.disciplines || [];
  } catch {
    return [];
  }
}

export async function mountChatJoin(root) {
  const token = joinTokenFromHash();
  root.innerHTML = `
    <section class="panel chat-join" data-testid="maker-chat-join">
      <h2>Join group chat</h2>
      <p class="muted">Sign in or create an account on this Nimbusware instance, then join with your invite.</p>
      <form id="chat-join-form" class="chat-join-form">
        <label>Username <input name="username" required autocomplete="username" /></label>
        <label>Password <input name="password" type="password" required autocomplete="current-password" /></label>
        <label class="chat-join-signup-only">Display name
          <input name="display_name" autocomplete="name" />
        </label>
        <label>Your discipline
          <select name="user_discipline" data-testid="maker-chat-join-discipline">
            <option value="">— pick later —</option>
          </select>
        </label>
        <p id="chat-join-invite-hint" class="muted" hidden data-testid="maker-chat-join-invite-hint"></p>
        <div class="actions">
          <button type="submit" name="mode" value="signin">Sign in & join</button>
          <button type="submit" name="mode" value="signup" class="btn btn--secondary">Create account & join</button>
        </div>
      </form>
      <p id="chat-join-error" class="error" hidden></p>
    </section>`;

  const disciplineSelect = root.querySelector("[data-testid='maker-chat-join-discipline']");
  const disciplines = await loadDisciplineOptions();
  for (const d of disciplines) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = d.display_name || d.id;
    disciplineSelect?.appendChild(opt);
  }

  if (!token) {
    const err = root.querySelector("#chat-join-error");
    if (err) {
      err.hidden = false;
      err.textContent = "Missing invite token in URL.";
    }
    return;
  }

  try {
    const preview = await apiJson(`/chat/join-preview?token=${encodeURIComponent(token)}`);
    const hint = root.querySelector("#chat-join-invite-hint");
    if (hint) {
      const role = String(preview.role || "session_read").replace("session_", "");
      const parts = [`Invited as ${role}`];
      if (preview.recommended_discipline) {
        parts.push(`suggested discipline: ${preview.recommended_discipline}`);
        if (disciplineSelect) disciplineSelect.value = preview.recommended_discipline;
      }
      hint.textContent = parts.join(" · ");
      hint.hidden = false;
    }
  } catch {
    /* preview optional */
  }

  root.querySelector("#chat-join-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const form = ev.currentTarget;
    const submitter = ev.submitter;
    const mode = submitter?.value === "signup" ? "signup" : "signin";
    const data = new FormData(form);
    const username = String(data.get("username") || "").trim();
    const password = String(data.get("password") || "");
    const displayName = String(data.get("display_name") || "").trim();
    const userDiscipline = String(data.get("user_discipline") || "").trim();
    const errEl = root.querySelector("#chat-join-error");
    try {
      await ensureSignedIn(username, password, displayName, mode);
      const joinBody = { token };
      if (userDiscipline) joinBody.user_discipline = userDiscipline;
      const joined = await apiJson("/chat/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(joinBody),
      });
      const sessionId = joined.session_id;
      window.location.hash = `/chat?session_id=${encodeURIComponent(sessionId)}`;
    } catch (e) {
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = String(e.message || e);
      }
    }
  });
}
