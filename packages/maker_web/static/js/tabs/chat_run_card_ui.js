import { apiJson } from "../api-client.js";
import { contractGateFromTimeline, contractGateCardHtml } from "../contract_gate_ui.js";
import { deployStateFromTimeline } from "../deploy_cockpit.js";
import { appendTheaterLine } from "../theater-renderer.js";
import { loadRunCardAgents } from "./chat_agents_ui.js";
import { workTypeLabel } from "./chat_session_ui.js";

const SESSION_KEY = "maker_chat_session_id";

export const FOLLOW_LIVE_KEY = "maker_chat_theater_follow_live";
const THEATER_CAP_DIGEST = 12;
const THEATER_CAP_LIVE = 96;

export function theaterCap() {
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

export function previewUrlFromDevEnvStatus(body) {
  if (!body?.active) return null;
  const session = body.session;
  if (!session || typeof session !== "object") return null;
  const url = session.frontend_base_url || session.base_url || session.api_base_url;
  const trimmed = String(url || "").trim();
  return trimmed || null;
}

function refreshChatContractGate(card, events) {
  if (!card) return;
  let gateEl = card.querySelector(".chat-run-card__contract-gate");
  const gate = contractGateFromTimeline(events);
  if (gate.state === "pending" && !gate.detail) {
    gateEl?.remove();
    return;
  }
  if (!gateEl) {
    gateEl = document.createElement("div");
    gateEl.className = "chat-run-card__contract-gate";
    const theater = card.querySelector(".chat-run-card__theater");
    card.insertBefore(gateEl, theater);
  }
  gateEl.innerHTML = contractGateCardHtml(gate, { testIdPrefix: "maker-chat" });
}

export async function refreshChatRunPreview(card, runId) {
  if (!card || !runId) return;
  let strip = card.querySelector(".chat-run-card__preview");
  if (!strip) {
    strip = document.createElement("p");
    strip.className = "chat-run-card__preview actions muted";
    strip.dataset.testid = "maker-chat-run-preview";
    const theater = card.querySelector(".chat-run-card__theater");
    card.insertBefore(strip, theater);
  }
  try {
    const [st, timeline] = await Promise.all([
      apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/status`),
      apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=80`).catch(() => ({ events: [] })),
    ]);
    const events = timeline.events || [];
    refreshChatContractGate(card, events);
    const deploy = deployStateFromTimeline(events);
    strip.replaceChildren();
    const parts = [];
    const url = previewUrlFromDevEnvStatus(st);
    if (url) {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Open preview";
      link.dataset.testid = "maker-chat-open-preview";
      parts.push(link);
    } else if (st.active) {
      const warming = document.createElement("span");
      warming.textContent = "Preview warming up…";
      parts.push(warming);
    }
    for (const [label, liveUrl, testId] of [
      ["Live API", deploy.apiUrl, "maker-chat-live-api"],
      ["Live web", deploy.webUrl, "maker-chat-live-web"],
    ]) {
      if (!liveUrl) continue;
      if (parts.length) parts.push(document.createTextNode(" · "));
      const link = document.createElement("a");
      link.href = liveUrl;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = label;
      link.dataset.testid = testId;
      parts.push(link);
    }
    if (!parts.length) {
      strip.hidden = true;
      return;
    }
    for (const node of parts) strip.append(node);
    strip.hidden = false;
  } catch {
    strip.hidden = true;
    strip.textContent = "";
  }
}

export function ensureRunCard(root, runId, { workType = "", status = "running" } = {}) {
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
  void refreshChatRunPreview(card, runId);
  return card;
}

export async function loadRunCardOperatorProfile(root, runId) {
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

export async function loadRunCardTrust(root, runId) {
  await loadRunCardOperatorProfile(root, runId);
}

function trimTheaterLines(container, cap) {
  if (!container) return;
  const lines = container.querySelectorAll(".theater-line, .chat-thread-line--theater");
  while (lines.length > cap) {
    lines[0].remove();
  }
}

export function appendTheaterToThread(root, runId, msg) {
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
