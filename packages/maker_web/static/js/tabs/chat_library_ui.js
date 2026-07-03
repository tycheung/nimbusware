import { apiJson } from "../api-client.js";

let _activeFolderId = "";
let _activeTag = "";

export async function refreshChatLibrary(
  root,
  projectId,
  { activeSessionId, loadSession } = {},
) {
  const panel = root.querySelector("[data-testid='maker-chat-library']");
  if (!panel || !projectId) return;
  try {
    const body = await apiJson(`/chat/folders?project_id=${encodeURIComponent(projectId)}`);
    const folders = body.folders || [];
    panel.replaceChildren();
    const title = document.createElement("h4");
    title.textContent = "Library";
    panel.appendChild(title);
    const allBtn = document.createElement("button");
    allBtn.type = "button";
    allBtn.className = _activeFolderId
      ? "chat-library-folder"
      : "chat-library-folder chat-library-folder--active";
    allBtn.dataset.testid = "maker-chat-library-all";
    allBtn.textContent = "All sessions";
    allBtn.addEventListener("click", async () => {
      _activeFolderId = "";
      await refreshChatLibrary(root, projectId, { activeSessionId, loadSession });
    });
    panel.appendChild(allBtn);
    for (const folder of folders) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        folder.folder_id === _activeFolderId
          ? "chat-library-folder chat-library-folder--active"
          : "chat-library-folder";
      btn.dataset.testid = `maker-chat-library-folder-${folder.folder_id}`;
      btn.textContent = folder.name;
      btn.addEventListener("click", async () => {
        _activeFolderId = folder.folder_id;
        await refreshChatLibrary(root, projectId, { activeSessionId, loadSession });
      });
      panel.appendChild(btn);
    }
    const tagFilter = document.createElement("input");
    tagFilter.type = "search";
    tagFilter.placeholder = "Filter by tag…";
    tagFilter.className = "chat-library-tag-filter";
    tagFilter.dataset.testid = "maker-chat-library-tag-filter";
    tagFilter.value = _activeTag;
    tagFilter.addEventListener("change", async () => {
      _activeTag = tagFilter.value.trim();
      await refreshChatLibrary(root, projectId, { activeSessionId, loadSession });
    });
    panel.appendChild(tagFilter);
    const list = document.createElement("ul");
    list.className = "chat-library-session-list";
    list.dataset.testid = "maker-chat-library-sessions";
    panel.appendChild(list);
    const sessions = await apiJson(`/chat/sessions?project_id=${encodeURIComponent(projectId)}`);
    const tagNeedle = _activeTag.toLowerCase();
    for (const session of sessions || []) {
      if (_activeFolderId && session.folder_id !== _activeFolderId) continue;
      const tags = session.tags || session.metadata?.tags || [];
      if (tagNeedle && !tags.some((t) => String(t).toLowerCase().includes(tagNeedle))) continue;
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        session.session_id === activeSessionId
          ? "chat-session-item chat-session-item--active"
          : "chat-session-item";
      btn.dataset.testid = `maker-chat-library-session-${session.session_id}`;
      btn.textContent = session.title || `Session ${String(session.session_id).slice(0, 8)}`;
      btn.addEventListener("click", () => loadSession?.(session.session_id));
      li.appendChild(btn);
      list.appendChild(li);
    }
    panel.classList.remove("hidden");
  } catch {
    panel.classList.add("hidden");
  }
}
