import { apiJson, toast } from "../api-client.js";
import { refreshBranchPanel } from "./chat_branch_ui.js";
import { closeInviteModal, unbindSessionStream } from "./chat_collab_ui.js";
import { CHAT_WORK_TYPES, chatLayoutHtml } from "./chat_shell_html.js";
import { createChatSessionApi } from "./chat_session_lifecycle.js";
import { branchPanelCallbacks, renderMessagesFromSession } from "./chat_thread_ui.js";
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
  mountScopeDiscoveryIfNeeded,
} from "./chat_composer_ui.js";
import {
  bindChatTheaterForRun,
  ensureRunCard,
  wireChatOperatorRibbons,
  wireFollowLiveToggle,
} from "./chat_theater_ui.js";
import { wireChatMentionAutocomplete } from "../chat_mention_ui.js";
import { mountSoloHatChips, mountSoloHatCoachHint } from "./chat_solo_hat_ui.js";

export async function mountChat(root) {
  root.innerHTML = chatLayoutHtml();

  wireFollowLiveToggle(root);
  mountAutopilotLadderHint(root);
  mountSoloHatChips(root);
  mountSoloHatCoachHint(root);

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
  const hashSessionId = hashParams.get("session_id") || "";
  const workSel = root.querySelector("#chat-work-type");
  const msgEl = root.querySelector("#chat-message");
  const INTENT_HINTS = {
    patch: "Describe the bug or paste a failing test name…",
    slice: "Describe the feature to add or change…",
    factory: "Describe the app you want (e.g. todo app with web UI and API)…",
    campaign: "Describe the product you want built end-to-end…",
  };
  if (intent && CHAT_WORK_TYPES.includes(intent) && workSel) {
    workSel.value = intent;
    if (msgEl && INTENT_HINTS[intent]) msgEl.placeholder = INTENT_HINTS[intent];
  }
  if (msgEl && deepPrompt && !msgEl.value.trim()) {
    msgEl.value = deepPrompt;
  }
  wireChatMentionAutocomplete(msgEl);
  root.querySelectorAll("[data-interjection-message]").forEach((el) => wireChatMentionAutocomplete(el));

  const sessionApi = createChatSessionApi(root, { chatResumeEnabled });
  if (hashSessionId) sessionApi.setSessionId(hashSessionId);
  sessionApi.wireSessionControls(sel);

  let startPending = false;
  let theaterHandle = null;
  let forkReplaySeq = null;

  async function runStart(workType) {
    const sessionId = sessionApi.getSessionId();
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
    const sessionId = sessionApi.getSessionId();
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
    const sessionId = sessionApi.getSessionId();
    await maybeOfferPatchEscalation(root, runId, sessionId);
    await maybeOfferSliceCampaignPromotion(root, runId, sessionId, (wt) => runStart(wt));
  }

  if (activeRunId) {
    ensureRunCard(root, activeRunId, { status: "active" });
    theaterHandle?.close();
    theaterHandle = bindChatTheaterForRun(
      root,
      activeRunId,
      sessionApi.getSessionId(),
      (wt) => runStart(wt),
    );
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
      await sessionApi.ensureSession(projectId);
      const sessionId = sessionApi.getSessionId();
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
      await mountScopeDiscoveryIfNeeded(root, classification, message, sessionApi.getSessionId());
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
      await sessionApi.ensureSession(saved);
    } catch {
      /* fresh session on send */
    }
  }

  if (hashSessionId) {
    try {
      await sessionApi.loadSession(hashSessionId);
    } catch {
      sessionApi.setSessionId("");
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
