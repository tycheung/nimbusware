import { apiJson, toast } from "../api-client.js";
import { autopilotRibbonHtml, wireAutopilotRibbon } from "../autopilot-ribbon.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { appendTheaterLine, theaterPayloadFromSse } from "../theater-renderer.js";
import { setActiveProjectId, setActiveRun, syncRunIdToShell } from "../session-hub.js";
import { refreshBranchPanel } from "./chat_branch_ui.js";
import {
  applyComposerForRole,
  refreshComputeNodes,
  refreshSessionSidebar,
  renderParticipantStrip,
  setCollabMyRole,
} from "./chat_session_ui.js";

const WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];
const SESSION_KEY = "maker_chat_session_id";
const RESUME_KEY = "maker_chat_resume_session";
const AUTOPILOT_LADDER_HINT_KEY = "maker_chat_autopilot_ladder_dismissed";
const FOLLOW_LIVE_KEY = "maker_chat_theater_follow_live";
const DEFAULT_PROFILE_KEY = "maker_default_autopilot_profile_id";
const THEATER_CAP_DIGEST = 12;
const THEATER_CAP_LIVE = 96;

const TURN_ROLE_LABELS = {
  user: "You",
  participant: "Guest",
  classifier: "Classifier",
  work_type_switch: "Mode",
  run_status: "Run",
  theater: "Agent",
  system: "System",
};

function theaterCap() {
  const follow = localStorage.getItem(FOLLOW_LIVE_KEY);
  if (follow == null || follow === "1" || follow === "true") return THEATER_CAP_LIVE;
  return THEATER_CAP_DIGEST;
}

function chatResumeEnabled() {
  const raw = localStorage.getItem(RESUME_KEY);
  return raw == null || raw === "1" || raw === "true";
}

function workTypeLabel(value) {
  if (!value || value === "auto") return "Auto";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function attachmentFields(root) {
  const targetRaw = root.querySelector("#chat-target-paths")?.value?.trim() || "";
  const paths = targetRaw
    .split(/[\n,]+/)
    .map((p) => p.trim())
    .filter(Boolean);
  const failingTest = root.querySelector("#chat-failing-test")?.value?.trim() || "";
  const stackTrace = root.querySelector("#chat-stack-trace")?.value?.trim() || "";
  const out = {};
  if (paths.length) out.target_paths = paths;
  if (failingTest) out.failing_test = failingTest;
  if (stackTrace) out.stack_trace = stackTrace;
  return out;
}

function attachmentPayload(root) {
  const fields = attachmentFields(root);
  return Object.keys(fields).length ? [fields] : [];
}

const ESCALATION_SLICE_OFFER =
  "Patch did not pass — widen to a micro-slice run? Switch work type to Slice or use Restore from here to branch.";

const ESCALATION_CAMPAIGN_OFFER =
  "Slice keeps replanning or failing — promote to an autonomous campaign for broader delivery?";

function turnRoleLabel(turn) {
  const role = turn.role || turn.kind || "system";
  return TURN_ROLE_LABELS[role] || "System";
}

function renderTurnLine(thread, turn) {
  const role = turn.role || turn.kind || "system";
  const li = document.createElement("li");
  const cssRole = role === "participant" ? "participant" : role === "user" ? "user" : "system";
  li.className = `chat-thread-line chat-thread-line--${cssRole}`;
  if (role !== "user" && role !== "participant") li.classList.add(`chat-thread-line--${role}`);
  if (role === "participant") li.classList.add("chat-thread-line--participant");
  li.dataset.turnId = turn.turn_id || "";
  if (turn.turn_id) li.dataset.testid = `maker-chat-turn-${turn.turn_id}`;

  const label = document.createElement("strong");
  label.textContent = turnRoleLabel(turn);
  li.appendChild(label);
  li.appendChild(document.createTextNode(` ${turn.text || ""}`));

  if (role === "classifier" && turn.payload?.work_type) {
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = ` → ${workTypeLabel(turn.payload.work_type)}`;
    li.appendChild(meta);
  }

  if (role === "user" && turn.turn_id) {
    const actions = document.createElement("span");
    actions.className = "chat-turn-actions";
    const forkBtn = document.createElement("button");
    forkBtn.type = "button";
    forkBtn.className = "linkish";
    forkBtn.textContent = "Restore from here";
    forkBtn.dataset.testid = `maker-chat-fork-${turn.turn_id}`;
    forkBtn.addEventListener("click", () => li.dispatchEvent(new CustomEvent("chat-fork", { bubbles: true })));
    actions.appendChild(forkBtn);
    li.appendChild(actions);
  }
  thread.appendChild(li);
  thread.scrollTop = thread.scrollHeight;
}

function renderMessagesFromSession(root, session) {
  if (session?.my_participant_role != null) {
    setCollabMyRole(session.my_participant_role);
  }
  renderParticipantStrip(root, session);
  applyComposerForRole(root);
  const thread = root.querySelector("#chat-thread");
  if (!thread) return;
  thread.replaceChildren();
  const turns = session.turns?.length ? session.turns : null;
  if (turns) {
    for (const turn of turns) {
      renderTurnLine(thread, turn);
    }
    return;
  }
  for (const msg of session.messages || []) {
    renderTurnLine(thread, {
      turn_id: msg.turn_id,
      role: msg.role === "user" ? "user" : msg.kind || "system",
      kind: msg.kind,
      text: msg.text,
      payload: msg.payload,
    });
  }
}

function branchPanelCallbacks(root) {
  return { onSessionUpdated: (session) => renderMessagesFromSession(root, session) };
}

function renderClassifierCard(root, classification, { onAccept, onOverride }) {
  const mount = root.querySelector("#chat-classifier-mount");
  if (!mount) return;
  mount.replaceChildren();

  const card = document.createElement("article");
  card.className = "panel chat-classifier-card";
  card.dataset.testid = "maker-chat-classifier-card";

  const wt = String(classification.work_type || "slice");
  const confidence =
    classification.confidence != null ? Math.round(Number(classification.confidence) * 100) : null;
  const headline = document.createElement("h4");
  headline.textContent = `Suggested: ${workTypeLabel(wt)}${confidence != null ? ` (${confidence}% confidence)` : ""}`;
  card.appendChild(headline);

  if (classification.rationale) {
    const rationale = document.createElement("p");
    rationale.className = "muted";
    rationale.textContent = classification.rationale;
    card.appendChild(rationale);
  }

  const chips = document.createElement("div");
  chips.className = "actions chat-action-chips";

  const accept = document.createElement("button");
  accept.type = "button";
  accept.className = "primary";
  accept.textContent = `Start as ${workTypeLabel(wt)}`;
  accept.dataset.testid = "maker-chat-accept-chip";
  accept.addEventListener("click", () => onAccept(wt));
  chips.appendChild(accept);

  for (const alt of WORK_TYPES.filter((t) => t !== "auto" && t !== wt)) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.textContent = workTypeLabel(alt);
    chip.dataset.testid = `maker-chat-override-chip-${alt}`;
    chip.addEventListener("click", () => onOverride(alt));
    chips.appendChild(chip);
  }

  card.appendChild(chips);
  mount.appendChild(card);
}

function defaultAutopilotProfileId() {
  return localStorage.getItem(DEFAULT_PROFILE_KEY)?.trim() || "";
}

async function startRunFromSession(
  sessionId,
  workType,
  root,
  projectId,
  { replayFromSeq, alignRunReplay } = {},
) {
  const message = root.querySelector("#chat-message")?.value?.trim() || "";
  const patchContext = attachmentFields(root);
  const dropdown = root.querySelector("#chat-work-type")?.value || "auto";
  const source = dropdown === "auto" ? "classifier" : "operator_override";

  const startPayload = {
    work_type: workType,
    work_type_source: source,
  };
  const profileId = defaultAutopilotProfileId();
  if (profileId) startPayload.autopilot_profile_id = profileId;
  if (message) {
    startPayload.requirements = { business_prompt: message };
  }
  if (workType === "patch" && Object.keys(patchContext).length) {
    startPayload.patch_context = patchContext;
  }
  if (alignRunReplay && replayFromSeq != null) {
    startPayload.align_run_replay = true;
    startPayload.replay_from_seq = replayFromSeq;
  }

  const body = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(startPayload),
  });

  const runId = body.run_id || body.campaign_id || body.id;
  if (!runId) throw new Error("Start response missing run_id");

  if (projectId) {
    setActiveProjectId(projectId);
    setActiveRun(projectId, runId);
  }
  syncRunIdToShell(runId);
  const thread = root.querySelector("#chat-thread");
  if (thread && body.turn) {
    renderTurnLine(thread, body.turn);
  }
  ensureRunCard(root, runId, { workType, status: "running" });
  window.location.hash = `/chat?run_id=${encodeURIComponent(runId)}`;
  if (body.replay_alignment?.replay_started) {
    toast(
      `${workTypeLabel(workType)} run started (replay from seq ${body.replay_alignment.from_store_seq})`,
      "success",
    );
  } else {
    toast(`${workTypeLabel(workType)} run started`, "success");
  }
  root.querySelector("#chat-classifier-mount")?.replaceChildren();
  root.querySelector("#chat-message").value = "";
  return runId;
}

async function switchWorkType(root, sessionId, turnId, workType, { replayFromSeq } = {}) {
  const payload = { work_type: workType };
  if (replayFromSeq != null) {
    payload.align_run_replay = true;
    payload.replay_from_seq = replayFromSeq;
  }
  const updated = await apiJson(
    `/chat/sessions/${encodeURIComponent(sessionId)}/turns/${encodeURIComponent(turnId)}/switch-mode`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const select = root.querySelector("#chat-work-type");
  if (select) select.value = workType;
  renderMessagesFromSession(root, updated);
  if (replayFromSeq != null) {
    toast(`Mode: ${workTypeLabel(workType)} (replay seq ${replayFromSeq} on next start)`, "success");
  } else {
    toast(`Mode: ${workTypeLabel(workType)}`, "success");
  }
  return updated;
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
  summary.append(wt, st, trust);
  card.appendChild(summary);
  const agents = document.createElement("div");
  agents.className = "chat-run-card__agents muted";
  agents.dataset.testid = "maker-chat-agents-strip";
  card.appendChild(agents);
  void loadRunCardAgents(card, runId);
  const theaterList = document.createElement("ul");
  theaterList.className = "chat-run-card__theater";
  theaterList.dataset.testid = "maker-chat-run-theater";
  card.appendChild(theaterList);
  thread.appendChild(card);
  loadRunCardTrust(root, runId);
  return card;
}

function showAgentBatteryPopover(anchor, detail) {
  document.querySelectorAll(".chat-agent-popover").forEach((el) => el.remove());
  const pop = document.createElement("div");
  pop.className = "chat-agent-popover";
  pop.dataset.testid = "maker-chat-agent-popover";
  const kind =
    detail.providerKind === "cloud" ? "cloud API" : "Ollama local";
  pop.innerHTML = `
    <strong>${detail.displayName}</strong>
    <div>Model: ${detail.modelId}</div>
    <div>Provider: ${detail.providerId} (${kind})</div>
    <div class="chat-agent-popover__actions">
      <button type="button" class="btn btn--sm" data-action="hub">Open Model Hub</button>
      ${
        detail.providerKind !== "cloud"
          ? `<button type="button" class="btn btn--sm" data-action="pull">Pull ${detail.modelId}</button>`
          : ""
      }
    </div>`;
  pop.querySelector('[data-action="hub"]')?.addEventListener("click", () => {
    const section = detail.providerKind === "cloud" ? "api-connections" : "local";
    window.location.hash = `#/models?section=${section}`;
    pop.remove();
  });
  pop.querySelector('[data-action="pull"]')?.addEventListener("click", async () => {
    try {
      await apiJson("/platform/ollama/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: detail.modelId }),
      });
      toast(`Pull queued: ${detail.modelId}`, "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
    pop.remove();
  });
  const rect = anchor.getBoundingClientRect();
  pop.style.position = "fixed";
  pop.style.top = `${rect.bottom + 4}px`;
  pop.style.left = `${rect.left}px`;
  document.body.appendChild(pop);
  const close = (ev) => {
    if (!pop.contains(ev.target) && ev.target !== anchor) {
      pop.remove();
      document.removeEventListener("click", close);
    }
  };
  setTimeout(() => document.addEventListener("click", close), 0);
}

async function loadRunCardAgents(card, runId) {
  const strip = card?.querySelector(".chat-run-card__agents");
  if (!strip) return;
  try {
    const body = await apiJson("/platform/model-bindings/defaults");
    const roles = (body.roles || []).slice(0, 4);
    strip.replaceChildren();
    const label = document.createElement("span");
    label.textContent = "Agents: ";
    strip.appendChild(label);
    for (const row of roles) {
      const binding = row.binding || {};
      const wrap = document.createElement("span");
      wrap.className = "chat-agent-badge-wrap";
      const badge = document.createElement("button");
      badge.type = "button";
      badge.className = "chat-agent-badge";
      badge.dataset.testid = `maker-chat-agent-${row.agent_role}`;
      const model = binding.model_id || "default";
      const provider = binding.provider_id || "ollama";
      badge.textContent = `${row.display_name || row.agent_role} · ${model}`;
      badge.title = "Swap model";
      badge.onclick = async () => {
        const next = window.prompt(`Model id for ${row.agent_role}`, model);
        if (!next || next === model) return;
        try {
          await apiJson(`/runs/${encodeURIComponent(runId)}/model-bindings/swap`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent_role: row.agent_role,
              provider_id: provider,
              provider_kind: binding.provider_kind || "local",
              model_id: next,
            }),
          });
          toast(`Swapped ${row.agent_role} to ${next}`, "success");
          await loadRunCardAgents(card, runId);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      };
      const info = document.createElement("button");
      info.type = "button";
      info.className = "chat-agent-info";
      info.textContent = "ⓘ";
      info.title = "Battery details";
      info.dataset.testid = `maker-chat-agent-info-${row.agent_role}`;
      info.onclick = (ev) => {
        ev.stopPropagation();
        showAgentBatteryPopover(info, {
          agentRole: row.agent_role,
          displayName: row.display_name || row.agent_role,
          modelId: model,
          providerId: provider,
          providerKind: binding.provider_kind || "local",
        });
      };
      wrap.append(badge, info);
      strip.appendChild(wrap);
    }
  } catch {
    strip.textContent = "Agents: —";
  }
}

async function loadRunCardTrust(root, runId) {
  const card = root.querySelector(`[data-run-id="${runId}"]`);
  const trust = card?.querySelector("[data-run-trust]");
  if (!trust) return;
  try {
    const ap = await apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`);
    trust.textContent = `Trust ${ap.level ?? "?"} · ${ap.name || "Custom"}`;
  } catch {
    trust.textContent = "Trust —";
  }
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

  return openSseStream(`/runs/${encodeURIComponent(runId)}/theater/stream`, {
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

async function maybeOfferSliceCampaignPromotion(root, runId, sessionId, onStartRun) {
  if (!runId) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline`);
    const events = timeline.events || [];
    let sliceRun = false;
    let gateFail = false;
    let replanCount = 0;
    for (const ev of events) {
      const meta = ev.metadata || {};
      if (ev.event_type === "run.created") {
        sliceRun = String(meta.work_type || "").toLowerCase() === "slice";
      }
      const payload = ev.payload || {};
      if (String(payload.stage_name || "") === "slice.gate") {
        if (String(meta.slice_gate_verdict || "").toUpperCase() === "FAIL") gateFail = true;
      }
      if (ev.event_type === "slice.replan" || String(payload.stage_name || "") === "slice.replan") {
        replanCount += 1;
      }
    }
    if (!sliceRun || (!gateFail && replanCount < 2)) return;
    const thread = root.querySelector("#chat-thread");
    if (!thread || thread.querySelector('[data-testid="maker-chat-escalation-campaign"]')) return;
    const li = document.createElement("li");
    li.className = "chat-thread-line chat-thread-line--system";
    li.dataset.testid = "maker-chat-escalation-campaign";
    li.appendChild(document.createTextNode(ESCALATION_CAMPAIGN_OFFER));
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Switch to Campaign";
    btn.dataset.testid = "maker-chat-escalate-campaign";
    btn.addEventListener("click", async () => {
      const userTurn = [...thread.querySelectorAll("[data-turn-id]")].findLast((el) =>
        el.classList.contains("chat-thread-line--user"),
      );
      const turnId = userTurn?.dataset?.turnId;
      if (sessionId && turnId) {
        await switchWorkType(root, sessionId, turnId, "campaign");
        const select = root.querySelector("#chat-work-type");
        if (select) select.value = "campaign";
        if (onStartRun) await onStartRun("campaign");
      }
    });
    li.appendChild(btn);
    thread.appendChild(li);
  } catch {}
}

async function maybeOfferPatchEscalation(root, runId, sessionId) {
  if (!runId) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline`);
    const events = timeline.events || [];
    let patchRun = false;
    let patchFailed = false;
    for (const ev of events) {
      const meta = ev.metadata || {};
      if (ev.event_type === "run.created") {
        const wt = String(meta.work_type || "").toLowerCase();
        patchRun = wt === "patch" || Boolean(meta.patch_effective?.enabled);
      }
      const payload = ev.payload || {};
      if (String(payload.stage_name || "") === "slice.gate") {
        if (String(meta.slice_gate_verdict || "").toUpperCase() === "FAIL") patchFailed = true;
      }
    }
    if (!patchRun || !patchFailed) return;
    const thread = root.querySelector("#chat-thread");
    if (!thread || thread.querySelector('[data-testid="maker-chat-escalation-slice"]')) return;
    const li = document.createElement("li");
    li.className = "chat-thread-line chat-thread-line--system";
    li.dataset.testid = "maker-chat-escalation-slice";
    li.textContent = ESCALATION_SLICE_OFFER;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Switch to Slice";
    btn.dataset.testid = "maker-chat-escalate-slice";
    btn.addEventListener("click", async () => {
      const userTurn = [...thread.querySelectorAll("[data-turn-id]")].findLast((el) =>
        el.classList.contains("chat-thread-line--user"),
      );
      const turnId = userTurn?.dataset?.turnId;
      if (sessionId && turnId) await switchWorkType(root, sessionId, turnId, "slice");
    });
    li.appendChild(btn);
    thread.appendChild(li);
  } catch {}
}

async function steerActiveRun(root, runId, message) {
  const prefixed = message.startsWith("[") ? message : `[steer] ${message}`;
  await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: prefixed, priority: "next" }),
  });
  const thread = root.querySelector("#chat-thread");
  if (thread) {
    renderTurnLine(thread, { role: "system", text: "Steering queued for the active run." });
  }
  toast("Steering queued", "success");
}

function wireChatOperatorRibbons(root, runId) {
  const ribbons = root.querySelector("#chat-operator-ribbons");
  if (!ribbons || !runId) return;
  if (ribbons.dataset.wired === runId) return;
  ribbons.dataset.wired = runId;
  ribbons.classList.remove("hidden");

  root.querySelector("#chat-interjection-next")?.addEventListener("click", async () => {
    const msg = root.querySelector("#chat-interjection-message")?.value?.trim();
    if (!msg) return toast("Enter a message", "error");
    try {
      await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, priority: "next" }),
      });
      toast("Queued", "success");
      root.querySelector("#chat-interjection-message").value = "";
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  root.querySelector("#chat-interjection-last")?.addEventListener("click", async () => {
    const msg = root.querySelector("#chat-interjection-message")?.value?.trim();
    if (!msg) return toast("Enter a message", "error");
    try {
      await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, priority: "last" }),
      });
      toast("Queued", "success");
      root.querySelector("#chat-interjection-message").value = "";
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  wireAutopilotRibbon(root, runId);
  root.addEventListener(
    "autopilot-updated",
    () => loadRunCardTrust(root, runId),
    { once: false },
  );
  root.addEventListener(
    "autopilot-loaded",
    (ev) => {
      const card = root.querySelector(`[data-run-id="${runId}"] [data-run-trust]`);
      if (card && ev.detail) {
        card.textContent = `Trust ${ev.detail.level} · ${ev.detail.name || "Custom"}`;
      }
    },
    { once: true },
  );
}

function mountAutopilotLadderHint(root) {
  if (localStorage.getItem(AUTOPILOT_LADDER_HINT_KEY) === "1") return;
  if (root.querySelector("[data-testid='maker-chat-autopilot-hint']")) return;
  const hint = document.createElement("aside");
  hint.className = "panel chat-autopilot-hint";
  hint.dataset.testid = "maker-chat-autopilot-hint";
  const slider = root.querySelector("[data-autopilot-slider]");
  const level = slider?.value || "8";
  const p = document.createElement("p");
  p.innerHTML =
    `<strong>Autonomy ladder (trust ~${level}):</strong> ` +
    "Fix a bug (patch) → Build a feature (micro-slice) → Build an app (factory). " +
    "Adjust trust in the ribbon when a run is active.";
  hint.appendChild(p);
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "linkish";
  dismiss.textContent = "Dismiss";
  dismiss.dataset.testid = "maker-chat-autopilot-hint-dismiss";
  dismiss.addEventListener("click", () => {
    localStorage.setItem(AUTOPILOT_LADDER_HINT_KEY, "1");
    hint.remove();
  });
  hint.appendChild(dismiss);
  root.prepend(hint);
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

export async function mountChat(root) {
  root.innerHTML = `
    <div class="chat-layout">
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
          <div class="chat-interjection-ribbon panel" data-testid="maker-chat-interjection-ribbon">
            <h4>Interjection</h4>
            <textarea id="chat-interjection-message" rows="2" placeholder="Steer the next slice…" data-testid="maker-chat-interjection-input"></textarea>
            <div class="actions">
              <button type="button" id="chat-interjection-next" data-testid="maker-chat-interjection-next">Next</button>
              <button type="button" id="chat-interjection-last" data-testid="maker-chat-interjection-last">Last</button>
            </div>
          </div>
          ${autopilotRibbonHtml({ compact: true })}
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
    renderMessagesFromSession(root, existing);
    await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
    const projectId = String(root.querySelector("#chat-project-select")?.value || "");
    await refreshSessionSidebar(root, projectId, sessionId, loadSession);
    await refreshComputeNodes(root, sessionId);
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
          renderMessagesFromSession(root, existing);
          await refreshBranchPanel(root, sessionId, branchPanelCallbacks(root));
          await refreshSessionSidebar(root, projectId, sessionId, loadSession);
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
    await refreshComputeNodes(root, sessionId);
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
    if (projectId) await refreshSessionSidebar(root, projectId, "", loadSession);
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
  };
}

let chatUnmount = () => {};

export function unmountChat() {
  chatUnmount();
  chatUnmount = () => {};
}
