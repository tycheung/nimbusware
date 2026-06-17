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
        <div class="actions">
          <button type="submit" name="mode" value="signin">Sign in & join</button>
          <button type="submit" name="mode" value="signup" class="btn btn--secondary">Create account & join</button>
        </div>
      </form>
      <p id="chat-join-error" class="error" hidden></p>
    </section>`;

  if (!token) {
    const err = root.querySelector("#chat-join-error");
    if (err) {
      err.hidden = false;
      err.textContent = "Missing invite token in URL.";
    }
    return;
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
    const errEl = root.querySelector("#chat-join-error");
    try {
      await ensureSignedIn(username, password, displayName, mode);
      const joined = await apiJson("/chat/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
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
