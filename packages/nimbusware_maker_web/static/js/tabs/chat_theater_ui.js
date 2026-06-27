import { wireAutopilotRibbon } from "../autopilot-ribbon.js";
import { wireEnforcementRibbon } from "../enforcement-ribbon.js";
import { wireInterjectionRibbon } from "../interjection-ribbon.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { theaterPayloadFromSse } from "../theater-renderer.js";
import {
  maybeOfferPatchEscalation,
  maybeOfferSliceCampaignPromotion,
} from "./chat_escalation_ui.js";
import {
  appendTheaterToThread,
  FOLLOW_LIVE_KEY,
  loadRunCardOperatorProfile,
  loadRunCardTrust,
  refreshChatRunPreview,
  theaterCap,
} from "./chat_run_card_ui.js";

export {
  appendTheaterToThread,
  ensureRunCard,
  loadRunCardOperatorProfile,
  loadRunCardTrust,
  theaterCap,
} from "./chat_run_card_ui.js";

function bindChatTheaterForRun(root, runId, sessionId, onStartRun) {
  if (!runId) return null;
  let previewTimer = null;
  const schedulePreviewRefresh = () => {
    const card = root.querySelector(`[data-run-id="${runId}"]`);
    if (card) void refreshChatRunPreview(card, runId);
  };
  schedulePreviewRefresh();
  previewTimer = setInterval(schedulePreviewRefresh, 20_000);
  const mount = root.querySelector("#chat-theater-mount");
  if (mount) {
    mount.removeAttribute("hidden");
    if (!mount.querySelector(".chat-theater-lines")) {
      const ul = document.createElement("ul");
      ul.className = "chat-theater-lines";
      mount.appendChild(ul);
    }
    const exportLink = mount.querySelector(".chat-theater-export");
    if (exportLink) {
      exportLink.href = `/v1/runs/${encodeURIComponent(runId)}/theater/export`;
    }
  }
  let escalationQueued = false;

  const onGateBlock = () => {
    if (escalationQueued) return;
    escalationQueued = true;
    maybeOfferPatchEscalation(root, runId, sessionId).catch(() => {});
    maybeOfferSliceCampaignPromotion(root, runId, sessionId, onStartRun).catch(() => {});
  };

  const handleTheaterPayload = (data) => {
    const msg = theaterPayloadFromSse(data);
    if (!msg || (!msg.headline && !msg.body_md)) return;
    appendTheaterToThread(root, runId, msg);
    if (msg.message_kind === "gate" && msg.severity === "block") onGateBlock();
    schedulePreviewRefresh();
  };

  const stream = openSseStream(
    `/runs/${encodeURIComponent(runId)}/theater/stream?profile=chat&cap=${theaterCap()}`,
    {
      onEvent: {
        theater: (ev) => {
          const data = parseSseJson(ev);
          if (data) handleTheaterPayload(data);
        },
      },
      onMessage: (ev) => {
        const data = parseSseJson(ev);
        if (data) handleTheaterPayload(data);
      },
    },
  );
  const baseClose = stream.close.bind(stream);
  stream.close = () => {
    if (previewTimer) clearInterval(previewTimer);
    baseClose();
  };
  return stream;
}

function wireChatOperatorRibbons(root, runId) {
  const ribbons = root.querySelector("#chat-operator-ribbons");
  if (!ribbons || !runId) return;
  if (ribbons.dataset.wired === runId) return;
  ribbons.dataset.wired = runId;
  ribbons.classList.remove("hidden");

  wireInterjectionRibbon(root, runId, { showQueue: false });
  wireAutopilotRibbon(root, runId);
  wireEnforcementRibbon(root, runId);
  root.addEventListener(
    "autopilot-updated",
    () => loadRunCardOperatorProfile(root, runId),
    { once: false },
  );
  root.addEventListener(
    "autopilot-loaded",
    (ev) => {
      const chip = root.querySelector(`[data-run-id="${runId}"] [data-run-trust]`);
      if (chip && ev.detail) {
        chip.textContent = `Trust ${ev.detail.level} · ${ev.detail.name || "Custom"}`;
      }
    },
    { once: true },
  );
  root.addEventListener(
    "enforcement-updated",
    () => loadRunCardOperatorProfile(root, runId),
    { once: false },
  );
  root.addEventListener(
    "enforcement-loaded",
    (ev) => {
      const chip = root.querySelector(`[data-run-id="${runId}"] [data-run-enforcement]`);
      if (chip && ev.detail) {
        chip.textContent = `Enforce ${ev.detail.level} · ${ev.detail.name || "Custom"}`;
      }
    },
    { once: true },
  );
}

function wireFollowLiveToggle(root) {
  const box = root.querySelector("#chat-theater-follow-live");
  if (!box) return;
  const stored = localStorage.getItem(FOLLOW_LIVE_KEY);
  box.checked = stored == null || stored === "1" || stored === "true";
  box.addEventListener("change", () => {
    localStorage.setItem(FOLLOW_LIVE_KEY, box.checked ? "1" : "0");
  });
}

export { bindChatTheaterForRun, wireChatOperatorRibbons, wireFollowLiveToggle };
