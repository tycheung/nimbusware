import { apiJson } from "../api-client.js";
import { wireAutopilotRibbon } from "../autopilot-ribbon.js";
import { wireEnforcementRibbon } from "../enforcement-ribbon.js";
import { wireInterjectionRibbon } from "../interjection-ribbon.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { appendTheaterLine, theaterPayloadFromSse } from "../theater-renderer.js";
import { loadRunCardAgents } from "./chat_agents_ui.js";
import { workTypeLabel } from "./chat_thread_ui.js";
import {
  maybeOfferPatchEscalation,
  maybeOfferSliceCampaignPromotion,
} from "./chat_escalation_ui.js";

const SESSION_KEY = "maker_chat_session_id";

const FOLLOW_LIVE_KEY = "maker_chat_theater_follow_live";
const THEATER_CAP_DIGEST = 12;
const THEATER_CAP_LIVE = 96;
function theaterCap() {
  const follow = localStorage.getItem(FOLLOW_LIVE_KEY);
  if (follow == null || follow === "1" || follow === "true") return THEATER_CAP_LIVE;
  return THEATER_CAP_DIGEST;
}
async function agentStripContext() {
  const sessionId = sessionStorage.getItem(SESSION_KEY) || "";
  let computeNodes = [];
  if (sessionId) {
    try {
      const body = await apiJson(`/compute/nodes?session_id=${encodeURIComponent(sessionId)}`);
      computeNodes = body.nodes || [];
    } catch {
      computeNodes = [];
    }
  }
  return { sessionId: sessionId || null, computeNodes };
}
function ensureRunCard(root, runId, { workType = "", status = "running" } = {}) {
  const thread = root.querySelector("#chat-thread");
  if (!thread || !runId) return null;
  let card = thread.querySelector(`[data-run-id="${runId}"]`);
  if (card) return card;
  card = document.createElement("details");
  card.className = "chat-run-card";
  card.dataset.runId = runId;
  card.dataset.testid = `maker-chat-run-card-${runId}`;
  card.open = true;
  const summary = document.createElement("summary");
  summary.className = "chat-run-card__header";
  summary.dataset.testid = "maker-chat-run-card-header";
  const wt = document.createElement("span");
  wt.className = "chat-run-card__work-type";
  wt.textContent = workTypeLabel(workType) || "Run";
  const st = document.createElement("span");
  st.className = "chat-run-card__status muted";
  st.dataset.runStatus = "1";
  st.textContent = status;
  const trust = document.createElement("span");
  trust.className = "chat-run-card__trust muted";
  trust.dataset.runTrust = "1";
  trust.textContent = "Trust …";
  const enforcement = document.createElement("span");
  enforcement.className = "chat-run-card__enforcement muted";
  enforcement.dataset.runEnforcement = "1";
  enforcement.textContent = "Enforce …";
  summary.append(wt, st, trust, enforcement);
  card.appendChild(summary);
  const agents = document.createElement("div");
  agents.className = "chat-run-card__agents muted";
  agents.dataset.testid = "maker-chat-agents-strip";
  card.appendChild(agents);
  void agentStripContext().then((ctx) => loadRunCardAgents(card, runId, ctx));
  const theaterList = document.createElement("ul");
  theaterList.className = "chat-run-card__theater";
  theaterList.dataset.testid = "maker-chat-run-theater";
  card.appendChild(theaterList);
  thread.appendChild(card);
  loadRunCardOperatorProfile(root, runId);
  return card;
}

async function loadRunCardOperatorProfile(root, runId) {
  const card = root.querySelector(`[data-run-id="${runId}"]`);
  const trust = card?.querySelector("[data-run-trust]");
  const enforcement = card?.querySelector("[data-run-enforcement]");
  if (trust) {
    try {
      const ap = await apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`);
      trust.textContent = `Trust ${ap.level ?? "?"} · ${ap.name || "Custom"}`;
    } catch {
      trust.textContent = "Trust —";
    }
  }
  if (enforcement) {
    try {
      const ep = await apiJson(`/runs/${encodeURIComponent(runId)}/enforcement`);
      enforcement.textContent = `Enforce ${ep.level ?? "?"} · ${ep.name || "Custom"}`;
    } catch {
      enforcement.textContent = "Enforce —";
    }
  }
}

async function loadRunCardTrust(root, runId) {
  await loadRunCardOperatorProfile(root, runId);
}

function trimTheaterLines(container, cap) {
  if (!container) return;
  const lines = container.querySelectorAll(".theater-line, .chat-thread-line--theater");
  while (lines.length > cap) {
    lines[0].remove();
  }
}

function appendTheaterToThread(root, runId, msg) {
  const card = ensureRunCard(root, runId, {});
  const list = card?.querySelector(".chat-run-card__theater") || root.querySelector("#chat-thread");
  const li = appendTheaterLine(list, msg, {
    testid: msg.data_testid,
    lineClass: "theater-line chat-thread-line--theater",
  });
  if (msg.message_kind === "gate" && msg.severity === "block") {
    li?.classList.add("chat-thread-line--gate-block");
  }
  if (
    msg.data_testid?.includes("compaction") ||
    (msg.message_kind === "context" && /compact/i.test(String(msg.headline || "")))
  ) {
    li?.classList.add("theater-line--compaction");
  }
  const cap = theaterCap();
  trimTheaterLines(list, cap);
  const thread = root.querySelector("#chat-thread");
  if (thread) thread.scrollTop = thread.scrollHeight;
  const archive = root.querySelector("#chat-theater-mount .chat-theater-lines");
  if (archive && li) {
    archive.appendChild(li.cloneNode(true));
  }
}

function bindChatTheaterForRun(root, runId, sessionId, onStartRun) {
  if (!runId) return null;
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
  };

  return openSseStream(
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
  });
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

export {
  appendTheaterToThread,
  bindChatTheaterForRun,
  ensureRunCard,
  loadRunCardOperatorProfile,
  loadRunCardTrust,
  theaterCap,
  wireChatOperatorRibbons,
  wireFollowLiveToggle,
};
