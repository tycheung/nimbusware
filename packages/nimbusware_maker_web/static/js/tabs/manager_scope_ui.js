import { apiJson, toast } from "../api-client.js";
import { plainManifestApprovalText } from "./chat_discovery_ui.js";

function sessionIdFromUrl() {
  const hashQuery = window.location.hash.includes("?")
    ? window.location.hash.slice(window.location.hash.indexOf("?") + 1)
    : "";
  const params = new URLSearchParams(hashQuery);
  return params.get("session_id")?.trim() || "";
}

export async function mountManagerScope(root) {
  root.innerHTML = `
    <section class="panel manager-scope-panel" data-testid="maker-manager-scope-panel">
      <h3>Scope approval</h3>
      <p class="muted">Review the stack manifest shared by the team lead and approve to unblock the run.</p>
      <label>Session ID
        <input id="manager-scope-session-id" type="text" data-testid="maker-manager-scope-session-id"
          placeholder="Paste session uuid from share link" />
      </label>
      <div class="actions">
        <button type="button" id="manager-scope-load" class="secondary" data-testid="maker-manager-scope-load">
          Load pending
        </button>
        <button type="button" id="manager-scope-approve" class="primary" data-testid="maker-manager-scope-approve" disabled>
          Approve manifest
        </button>
      </div>
      <article id="manager-scope-card" class="panel manager-scope-card hidden" data-testid="maker-manager-scope-card"></article>
      <p id="manager-scope-status" class="muted"></p>
    </section>`;

  const sessionInput = root.querySelector("#manager-scope-session-id");
  const card = root.querySelector("#manager-scope-card");
  const status = root.querySelector("#manager-scope-status");
  const approveBtn = root.querySelector("#manager-scope-approve");
  let pendingState = null;

  const fromUrl = sessionIdFromUrl();
  if (fromUrl && sessionInput) sessionInput.value = fromUrl;

  function renderPending(scope) {
    pendingState = scope;
    if (!card) return;
    card.replaceChildren();
    card.hidden = !scope;
    if (!scope) {
      if (approveBtn) approveBtn.disabled = true;
      return;
    }
    const manifest = scope.stack_manifest;
    const plain = document.createElement("p");
    plain.className = "chat-manifest-plain";
    plain.dataset.testid = "maker-manager-scope-plain";
    plain.textContent = plainManifestApprovalText(manifest, scope);
    card.appendChild(plain);
    if (scope.scope_confirmed) {
      if (status) status.textContent = "Already approved.";
      if (approveBtn) approveBtn.disabled = true;
    } else if (approveBtn) {
      approveBtn.disabled = false;
    }
  }

  root.querySelector("#manager-scope-load")?.addEventListener("click", async () => {
    const sessionId = sessionInput?.value?.trim() || "";
    if (!sessionId) {
      toast("Enter a session ID", "error");
      return;
    }
    try {
      const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/scope/pending`);
      if (body.scope_approved) {
        renderPending(body.scope_approved);
        if (status) status.textContent = "Manifest already approved.";
        return;
      }
      if (!body.scope_pending) {
        if (status) status.textContent = "No manifest pending approval for this session.";
        renderPending(null);
        return;
      }
      renderPending(body.scope_pending);
      if (status) status.textContent = "Pending manager approval.";
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  approveBtn?.addEventListener("click", async () => {
    const sessionId = sessionInput?.value?.trim() || "";
    if (!sessionId || !pendingState) return;
    approveBtn.disabled = true;
    try {
      const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/scope/approve`, {
        method: "POST",
      });
      renderPending(body.scope_approved || pendingState);
      if (status) status.textContent = "Manifest approved — team can start the run.";
      toast("Manifest approved", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
      approveBtn.disabled = false;
    }
  });

  if (fromUrl) {
    root.querySelector("#manager-scope-load")?.click();
  }
}
