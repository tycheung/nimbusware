import { apiJson, toast } from "../api-client.js";
import { autopilotRibbonHtml } from "../autopilot-ribbon.js";
import { enforcementRibbonHtml } from "../enforcement-ribbon.js";
import { chatInterjectionRibbonHtml, queueInterjection, wireInterjectionRibbon } from "../interjection-ribbon.js";
import { refreshBranchPanel } from "./chat_branch_ui.js";
import {
  applyComposerForRole,
  getCollabMyRole,
  refreshComputeNodes,
  refreshSessionSidebar,
  renderParticipantStrip,
  setCollabMyRole,
} from "./chat_session_ui.js";
import { refreshChatLibrary } from "./chat_library_ui.js";
import {
  bindSessionStream,
  closeInviteModal,
  mountCommentaryComposer,
  mountInviteButton,
  unbindSessionStream,
} from "./chat_collab_ui.js";
import { refreshHostTransferPanel } from "./chat_host_transfer_ui.js";
import { refreshAccessibleComputeTrigger } from "./accessible_compute_ui.js";
import { refreshSessionOptimizerPanel } from "./chat_optimizer_ui.js";

import { branchPanelCallbacks, renderMessagesFromSession, renderTurnLine, workTypeLabel } from "./chat_thread_ui.js";
import { switchWorkType } from "./chat_work_type.js";
import {
  maybeOfferPatchEscalation,
  maybeOfferSliceCampaignPromotion,
  steerActiveRun,
} from "./chat_escalation_ui.js";
import {
  attachmentPayload,
  chatResumeEnabled,
  mountAutopilotLadderHint,
  renderClassifierCard,
  startRunFromSession,
} from "./chat_composer_ui.js";
import {
  bindChatTheaterForRun,
  ensureRunCard,
  wireChatOperatorRibbons,
  wireFollowLiveToggle,
} from "./chat_theater_ui.js";
const WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];
const SESSION_KEY = "maker_chat_session_id";
const RESUME_KEY = "maker_chat_resume_session";

let sessionStreamTurnCount = 0;
let cachedCurrentUserId = null;

async function resolveCurrentUserId() {
  if (cachedCurrentUserId) return cachedCurrentUserId;
  try {
    const me = await apiJson("/auth/me");
    cachedCurrentUserId = me.user_id || null;
  } catch {
    cachedCurrentUserId = null;
  }
  return cachedCurrentUserId;
}

async function wireCollabSessionUi(root, sessionId, session) {
  if (!sessionId) return;
  renderMessagesFromSession(root, session);
  mountInviteButton(root, sessionId);
  await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
  await refreshSessionOptimizerPanel(root, sessionId, {
    workloadMode: session?.workload_distribution || "host_only",
  });
  mountCommentaryComposer(root, sessionId, (turn) => {
    const thread = root.querySelector("#chat-thread");
    if (thread && turn) renderTurnLine(thread, turn);
  });
  const userId = await resolveCurrentUserId();
  await refreshHostTransferPanel(root, sessionId, {
    currentUserId: userId,
    onReload: async () => {
      const existing = await apiJson(
        `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
      );
      renderMessagesFromSession(root, existing);
    },
  });
  sessionStreamTurnCount = session?.turns?.length || 0;
  bindSessionStream(root, sessionId, {
    onSession: async (data) => {
      if (data.participants?.length) {
        renderParticipantStrip(root, {
          participants: data.participants,
          host_user_id: session?.host_user_id,
        });
        mountInviteButton(root, sessionId);
      }
      await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
      const count = data.turn_count ?? sessionStreamTurnCount;
      if (count > sessionStreamTurnCount) {
        sessionStreamTurnCount = count;
        try {
          const existing = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
          );
          renderMessagesFromSession(root, existing);
        } catch {
          /* ignore */
        }
      }
    },
  });
}

export async function mountChat(root) {
  root.innerHTML = `
    <div class="chat-layout">
      <aside class="chat-library panel" data-testid="maker-chat-library"></aside>
      <aside class="chat-session-sidebar panel" data-testid="maker-chat-session-sidebar">
        <h4>Sessions</h4>
        <ul id="chat-session-list" class="chat-session-list"></ul>
        <button type="button" id="chat-new-session" class="linkish" data-testid="maker-chat-new-session">New session</button>
      </aside>
      <div class="chat-main">
        <section
          id="chat-compute-nodes"
          class="panel chat-compute-nodes muted"
          data-testid="maker-chat-compute-nodes"
          hidden
        >
          <h4>Compute</h4>
          <p class="chat-compute-nodes-caption">Session compute nodes</p>
          <ul id="chat-compute-nodes-list" class="chat-compute-nodes-list"></ul>
        </section>
        <section id="chat-operator-ribbons" class="chat-operator-ribbons hidden" data-testid="maker-chat-operator-ribbons">
          ${chatInterjectionRibbonHtml()}
          ${autopilotRibbonHtml({ compact: true })}
          ${enforcementRibbonHtml({ compact: true })}
        </section>
        <form id="chat-form" class="chat-form">
          <label>Project
            <select name="project_id" id="chat-project-select" data-testid="maker-chat-project-select" required></select>
          </label>
          <label>Work type
            <select name="work_type" id="chat-work-type" data-testid="maker-chat-work-type-select">
              ${WORK_TYPES.map((wt) => `<option value="${wt}">${workTypeLabel(wt)}</option>`).join("")}
            </select>
          </label>
          <label>Message
            <textarea name="message" id="chat-message" rows="4" required
              data-testid="maker-chat-message" placeholder="Describe the change, bug, or feature…"></textarea>
          </label>
          <fieldset class="chat-attachments">
            <legend>Attachments (optional)</legend>
            <label>File paths
              <textarea name="target_paths" id="chat-target-paths" rows="2"
                data-testid="maker-chat-target-path" placeholder="src/foo.py"></textarea>
            </label>
            <label>Failing test
              <input name="failing_test" id="chat-failing-test" type="text"
                data-testid="maker-chat-failing-test" placeholder="tests/test_foo.py::test_bar" />
            </label>
            <label>Stack trace
              <textarea name="stack_trace" id="chat-stack-trace" rows="3"
                data-testid="maker-chat-stack-trace" placeholder="AssertionError: …"></textarea>
            </label>
          </fieldset>
          <button type="submit" class="primary" data-testid="maker-chat-start">Send</button>
        </form>
        <aside id="chat-branch-panel" class="panel chat-branch-panel hidden" data-testid="maker-chat-branch-panel"></aside>
        <details id="chat-theater-mount" class="chat-theater-mount hidden" data-testid="maker-chat-theater-mount">
          <summary>
            Full run log (archive)
            <label class="chat-follow-live">
              <input type="checkbox" id="chat-theater-follow-live" data-testid="maker-chat-theater-follow-live" checked />
              Follow live
            </label>
            <a class="chat-theater-export linkish" href="#" download>Export transcript</a>
          </summary>
        </details>
        <ul id="chat-thread" class="chat-thread" data-testid="maker-chat-thread"></ul>
        <div id="chat-classifier-mount"></div>
      </div>
    </div>`;

  wireFollowLiveToggle(root);
  mountAutopilotLadderHint(root);

  const listing = await apiJson("/projects");
  const sel = root.querySelector("#chat-project-select");
  for (const p of listing.projects || []) {
    const opt = document.createElement("option");
    opt.value = p.project_id;
    opt.textContent = p.name || p.project_id;
    sel?.appendChild(opt);
  }
  const saved = sessionStorage.getItem("maker_active_project_id");
  if (saved && sel) sel.value = saved;

  const hashQuery = window.location.hash.includes("?")
    ? window.location.hash.slice(window.location.hash.indexOf("?") + 1)
    : "";
  const hashParams = new URLSearchParams(hashQuery);
  const intent = hashParams.get("intent");
  const deepPrompt = hashParams.get("prompt");
  const workSel = root.querySelector("#chat-work-type");
  const msgEl = root.querySelector("#chat-message");
  const INTENT_HINTS = {
    patch: "Describe the bug or paste a failing test name…",
    slice: "Describe the feature to add or change…",
    factory: "Describe the app you want (e.g. todo API with REST endpoints)…",
  };
  if (intent && WORK_TYPES.includes(intent) && workSel) {
    workSel.value = intent;
    if (msgEl && INTENT_HINTS[intent]) msgEl.placeholder = INTENT_HINTS[intent];
  }
  if (msgEl && deepPrompt && !msgEl.value.trim()) {
    msgEl.value = deepPrompt;
  }

  let sessionId = chatResumeEnabled() ? sessionStorage.getItem(SESSION_KEY) || "" : "";
  const hashSessionId = hashParams.get("session_id") || "";
  if (hashSessionId) sessionId = hashSessionId;
  let startPending = false;
  let theaterHandle = null;
  let forkReplaySeq = null;

  async function loadSession(sid) {
    sessionId = sid;
    sessionStorage.setItem(SESSION_KEY, sessionId);
    const existing = await apiJson(
      `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
    );
    await wireCollabSessionUi(root, sessionId, existing);
    await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
    const projectId = String(root.querySelector("#chat-project-select")?.value || "");
    await refreshSessionSidebar(root, projectId, sessionId, loadSession);
    await refreshChatLibrary(root, projectId, { activeSessionId: sessionId, loadSession });
    await refreshComputeNodes(root, sessionId);
    await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
  }

  async function ensureSession(projectId) {
    if (!chatResumeEnabled()) {
      sessionId = "";
    }
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
        sessionId = "";
      }
    }
    const session = await apiJson("/chat/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    });
    sessionId = String(session.session_id || "");
    sessionStorage.setItem(SESSION_KEY, sessionId);
    await refreshSessionSidebar(root, projectId, sessionId, loadSession);
    await refreshChatLibrary(root, projectId, { activeSessionId: sessionId, loadSession });
    await refreshComputeNodes(root, sessionId);
    await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
    await wireCollabSessionUi(root, sessionId, session);
    return sessionId;
  }

  root.querySelector("#chat-new-session")?.addEventListener("click", async () => {
    const projectId = String(root.querySelector("#chat-project-select")?.value || "");
    if (!projectId) return toast("Select a project", "error");
    sessionId = "";
    sessionStorage.removeItem(SESSION_KEY);
    await ensureSession(projectId);
    root.querySelector("#chat-thread")?.replaceChildren();
    toast("New session", "success");
  });

  sel?.addEventListener("change", async () => {
    const projectId = String(sel.value || "");
    sessionId = "";
    sessionStorage.removeItem(SESSION_KEY);
    if (projectId) {
      await refreshSessionSidebar(root, projectId, "", loadSession);
      await refreshChatLibrary(root, projectId, { activeSessionId: sessionId, loadSession });
    }
  });

  async function runStart(workType) {
    if (startPending || !sessionId) return;
    startPending = true;
    const startBtn = root.querySelector('[data-testid="maker-chat-start"]');
    if (startBtn) startBtn.disabled = true;
    try {
      const projectId = String(root.querySelector("#chat-project-select")?.value || "");
      const replayOpts =
        forkReplaySeq != null ? { replayFromSeq: forkReplaySeq, alignRunReplay: true } : {};
      const runId = await startRunFromSession(sessionId, workType, root, projectId, replayOpts);
      forkReplaySeq = null;
      theaterHandle?.close();
      theaterHandle = bindChatTheaterForRun(root, runId, sessionId, (wt) => runStart(wt));
      wireChatOperatorRibbons(root, runId);
      mountAutopilotLadderHint(root);
      await offerRunEscalations(runId);
    } catch (e) {
      toast(String(e.message || e), "error");
    } finally {
      startPending = false;
      if (startBtn) startBtn.disabled = false;
    }
  }

  root.querySelector("#chat-thread")?.addEventListener("chat-fork", async (ev) => {
    const turnEl = ev.target?.closest("[data-turn-id]");
    const turnId = turnEl?.dataset?.turnId;
    if (!turnId || !sessionId) return;
    const align = window.confirm("Fork from here? OK = new branch. Cancel = abort.");
    if (!align) return;
    const alignReplay = window.confirm("Align execution replay from this turn on next mode switch?");
    try {
      const updated = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/fork`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ turn_id: turnId }),
      });
      if (alignReplay) {
        const turn = (updated.turns || []).find((t) => t.turn_id === turnId);
        forkReplaySeq = turn?.event_seq ?? null;
      }
      renderMessagesFromSession(root, updated);
      await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
      toast("Forked — next message starts a new branch", "info");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  const activeRunId = hashParams.get("run_id") || "";

  async function offerRunEscalations(runId) {
    if (!runId) return;
    await maybeOfferPatchEscalation(root, runId, sessionId);
    await maybeOfferSliceCampaignPromotion(root, runId, sessionId, (wt) => runStart(wt));
  }

  if (activeRunId) {
    ensureRunCard(root, activeRunId, { status: "active" });
    theaterHandle?.close();
    theaterHandle = bindChatTheaterForRun(root, activeRunId, sessionId, (wt) => runStart(wt));
    wireChatOperatorRibbons(root, activeRunId);
    mountAutopilotLadderHint(root);
  }

  const steerDraft = sessionStorage.getItem("maker_plan_steer_draft");
  if (steerDraft) {
    const interjection = root.querySelector("#chat-interjection-message");
    if (interjection && !interjection.value.trim()) interjection.value = steerDraft;
    sessionStorage.removeItem("maker_plan_steer_draft");
  }

  root.querySelector("#chat-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (startPending) return;

    const message = root.querySelector("#chat-message")?.value?.trim() || "";
    if (!message) {
      toast("Enter a message", "error");
      return;
    }
    const projectId = String(root.querySelector("#chat-project-select")?.value || "");
    if (!projectId) {
      toast("Select a project", "error");
      return;
    }

    const runFromUrl =
      new URLSearchParams(window.location.hash.split("?")[1] || "").get("run_id") || "";
    if (runFromUrl && !message.toLowerCase().startsWith("/run")) {
      try {
        await steerActiveRun(root, runFromUrl, message);
        root.querySelector("#chat-message").value = "";
        return;
      } catch (e) {
        toast(String(e.message || e), "error");
        return;
      }
    }

    const dropdownWt = root.querySelector("#chat-work-type")?.value || "auto";
    const attachments = attachmentPayload(root);
    startPending = true;
    const startBtn = root.querySelector('[data-testid="maker-chat-start"]');
    if (startBtn) startBtn.disabled = true;

    try {
      await ensureSession(projectId);
      const turnResp = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/turns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: message, attachments }),
      });
      const session = await apiJson(
        `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
      );
      renderMessagesFromSession(root, session);
      await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));

      const classification = turnResp.classification || {};

      if (dropdownWt !== "auto") {
        startPending = false;
        if (startBtn) startBtn.disabled = false;
        await runStart(dropdownWt);
        return;
      }

      renderClassifierCard(root, classification, {
        onAccept: (wt) => runStart(wt),
        onOverride: (wt) => {
          const select = root.querySelector("#chat-work-type");
          if (select) select.value = wt;
          runStart(wt);
        },
      });
      const confidence = Number(classification.confidence ?? 1);
      if (confidence < 0.5) {
        toast("Low confidence — confirm work type before starting", "info");
      }
    } catch (e) {
      toast(String(e.message || e), "error");
    } finally {
      startPending = false;
      if (startBtn) startBtn.disabled = false;
    }
  });

  if (saved && chatResumeEnabled()) {
    try {
      await ensureSession(saved);
    } catch {
      /* fresh session on send */
    }
  }

  if (hashSessionId) {
    try {
      await loadSession(hashSessionId);
    } catch {
      sessionId = "";
      sessionStorage.removeItem(SESSION_KEY);
    }
  }

  if (activeRunId) {
    await offerRunEscalations(activeRunId);
  }

  chatUnmount = () => {
    theaterHandle?.close();
    theaterHandle = null;
    unbindSessionStream();
    closeInviteModal();
  };
}

let chatUnmount = () => {};

export function unmountChat() {
  chatUnmount();
  chatUnmount = () => {};
}
