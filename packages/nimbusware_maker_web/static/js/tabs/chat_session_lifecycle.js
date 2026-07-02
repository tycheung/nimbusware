import { apiJson, toast } from "../api-client.js";
import { refreshAccessibleComputeTrigger } from "./accessible_compute_ui.js";
import { wireCollabSessionUi } from "./chat_collab_wiring.js";
import { refreshChatLibrary } from "./chat_library_ui.js";
import {
  branchPanelCallbacks,
  getCollabMyRole,
  refreshBranchPanel,
  refreshComputeNodes,
  refreshSessionSidebar,
} from "./chat_session_ui.js";

const SESSION_KEY = "maker_chat_session_id";

export function createChatSessionApi(root, { chatResumeEnabled }) {
  let sessionId = chatResumeEnabled() ? sessionStorage.getItem(SESSION_KEY) || "" : "";

  function setSessionId(sid) {
    sessionId = sid;
    if (sid) sessionStorage.setItem(SESSION_KEY, sid);
    else sessionStorage.removeItem(SESSION_KEY);
  }

  async function afterSessionLoaded(projectId) {
    await refreshSessionSidebar(root, projectId, sessionId, loadSession);
    await refreshChatLibrary(root, projectId, { activeSessionId: sessionId, loadSession });
    await refreshComputeNodes(root, sessionId);
    await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
  }

  async function loadSession(sid) {
    setSessionId(sid);
    const existing = await apiJson(
      `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
    );
    await wireCollabSessionUi(root, sessionId, existing);
    await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
    const projectId = String(root.querySelector("#chat-project-select")?.value || "");
    await afterSessionLoaded(projectId);
  }

  async function ensureSession(projectId) {
    if (!chatResumeEnabled()) setSessionId("");
    if (sessionId) {
      try {
        const existing = await apiJson(
          `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
        );
        if (existing.project_id === projectId) {
          await wireCollabSessionUi(root, sessionId, existing);
          await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
          await refreshSessionSidebar(root, projectId, sessionId, loadSession);
          await refreshComputeNodes(root, sessionId);
          await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
          return sessionId;
        }
      } catch {
        setSessionId("");
      }
    }
    const session = await apiJson("/chat/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    setSessionId(String(session.session_id || ""));
    await afterSessionLoaded(projectId);
    await wireCollabSessionUi(root, sessionId, session);
    return sessionId;
  }

  function wireSessionControls(sel) {
    root.querySelector("#chat-new-session")?.addEventListener("click", async () => {
      const projectId = String(root.querySelector("#chat-project-select")?.value || "");
      if (!projectId) return toast("Select a project", "error");
      setSessionId("");
      await ensureSession(projectId);
      root.querySelector("#chat-thread")?.replaceChildren();
      toast("New session", "success");
    });

    sel?.addEventListener("change", async () => {
      const projectId = String(sel.value || "");
      setSessionId("");
      if (projectId) {
        await refreshSessionSidebar(root, projectId, "", loadSession);
        await refreshChatLibrary(root, projectId, { activeSessionId: sessionId, loadSession });
      }
    });
  }

  return {
    getSessionId: () => sessionId,
    setSessionId,
    loadSession,
    ensureSession,
    wireSessionControls,
  };
}
