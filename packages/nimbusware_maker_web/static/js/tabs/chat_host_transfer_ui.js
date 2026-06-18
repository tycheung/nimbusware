import { apiJson, toast } from "../api-client.js";
import { getCollabMyRole } from "./chat_session_ui.js";

function transferStatusLabel(status) {
  return String(status || "unknown").replace(/_/g, " ");
}

export async function refreshHostTransferPanel(root, sessionId, { currentUserId, onReload } = {}) {
  if (!sessionId) return;
  let panel = root.querySelector("[data-testid='maker-chat-host-transfer']");
  if (!panel) {
    panel = document.createElement("section");
    panel.className = "panel chat-host-transfer";
    panel.dataset.testid = "maker-chat-host-transfer";
    const main = root.querySelector(".chat-main");
    const compute = root.querySelector("#chat-compute-nodes");
    if (main && compute) {
      compute.insertAdjacentElement("afterend", panel);
    } else {
      main?.prepend(panel);
    }
  }
  try {
    const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer`);
    const transfers = body.transfers || [];
    const pending = transfers.find((t) => t.status === "pending");
    const frozen = transfers.find((t) => t.status === "frozen");
    const role = getCollabMyRole();
    panel.replaceChildren();
    const title = document.createElement("h4");
    title.textContent = "Host transfer";
    panel.appendChild(title);
    if (!transfers.length && role !== "session_admin") {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    const list = document.createElement("ul");
    list.className = "chat-host-transfer-list";
    for (const t of transfers.slice(0, 5)) {
      const li = document.createElement("li");
      li.textContent = `${transferStatusLabel(t.status)} → ${String(t.to_user_id).slice(0, 8)}…`;
      list.appendChild(li);
    }
    panel.appendChild(list);
    const actions = document.createElement("div");
    actions.className = "actions";
    if (role === "session_admin" && !pending && !frozen) {
      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = "Successor user UUID";
      input.dataset.testid = "maker-chat-host-transfer-target";
      const reqBtn = document.createElement("button");
      reqBtn.type = "button";
      reqBtn.textContent = "Request transfer";
      reqBtn.dataset.testid = "maker-chat-host-transfer-request";
      reqBtn.addEventListener("click", async () => {
        const uid = input.value.trim();
        if (!uid) return;
        try {
          await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ to_user_id: uid }),
          });
          toast("Transfer requested", "success");
          await refreshHostTransferPanel(root, sessionId, { currentUserId, onReload });
          onReload?.();
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      actions.append(input, reqBtn);
    }
    if (pending && currentUserId && pending.to_user_id === currentUserId) {
      const accept = document.createElement("button");
      accept.type = "button";
      accept.textContent = "Accept & freeze";
      accept.dataset.testid = "maker-chat-host-transfer-accept";
      accept.addEventListener("click", async () => {
        try {
          await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer/${pending.transfer_id}/accept`,
            { method: "POST" },
          );
          toast("Session frozen for cutover", "success");
          await refreshHostTransferPanel(root, sessionId, { currentUserId, onReload });
          onReload?.();
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      const decline = document.createElement("button");
      decline.type = "button";
      decline.className = "secondary";
      decline.textContent = "Decline";
      decline.addEventListener("click", async () => {
        try {
          await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer/${pending.transfer_id}/decline`,
            { method: "POST" },
          );
          toast("Transfer declined", "info");
          await refreshHostTransferPanel(root, sessionId, { currentUserId, onReload });
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      actions.append(accept, decline);
    }
    if (frozen && currentUserId && frozen.to_user_id === currentUserId) {
      const bundleBtn = document.createElement("button");
      bundleBtn.type = "button";
      bundleBtn.textContent = "Download bundle";
      bundleBtn.addEventListener("click", async () => {
        try {
          const body = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer/${frozen.transfer_id}/bundle`,
          );
          const blob = new Blob([JSON.stringify(body.manifest, null, 2)], {
            type: "application/json",
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `host-transfer-${frozen.transfer_id}.json`;
          a.click();
          URL.revokeObjectURL(url);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      const importInput = document.createElement("input");
      importInput.type = "file";
      importInput.accept = "application/json,.json";
      const importBtn = document.createElement("button");
      importBtn.type = "button";
      importBtn.textContent = "Import bundle";
      importBtn.addEventListener("click", () => importInput.click());
      importInput.addEventListener("change", async () => {
        const file = importInput.files?.[0];
        if (!file) return;
        try {
          const text = await file.text();
          const manifest = JSON.parse(text);
          await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/host-transfer/${frozen.transfer_id}/import`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ manifest }),
            },
          );
          toast("Transfer completed", "success");
          await refreshHostTransferPanel(root, sessionId, { currentUserId, onReload });
          onReload?.();
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      actions.append(bundleBtn, importBtn, importInput);
    }
    if (actions.childNodes.length) panel.appendChild(actions);
  } catch {
    panel.hidden = true;
  }
}
