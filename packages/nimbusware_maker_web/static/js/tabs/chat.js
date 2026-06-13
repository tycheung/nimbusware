import { apiJson, toast } from "../api-client.js";
import { openSseStream, parseSseJson, theaterLineText } from "../sse-client.js";
import { setActiveProjectId, setActiveRun, syncRunIdToShell } from "../session-hub.js";

const WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];
const SESSION_KEY = "maker_chat_session_id";
const RESUME_KEY = "maker_chat_resume_session";
const AUTOPILOT_LADDER_HINT_KEY = "maker_chat_autopilot_ladder_dismissed";
const THEATER_CAP = 12;

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

function renderTurnLine(thread, turn) {
  const li = document.createElement("li");
  const role = turn.role === "user" ? "user" : "system";
  li.className = `chat-thread-line chat-thread-line--${role}`;
  li.dataset.turnId = turn.turn_id || "";
  if (turn.turn_id) li.dataset.testid = `maker-chat-turn-${turn.turn_id}`;

  const label = document.createElement("strong");
  label.textContent = role === "user" ? "You" : "System";
  li.appendChild(label);
  li.appendChild(document.createTextNode(` ${turn.text || ""}`));

  if (turn.role === "user" && turn.turn_id) {
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
  const thread = root.querySelector("#chat-thread");
  if (!thread) return;
  thread.replaceChildren();
  for (const msg of session.messages || []) {
    renderTurnLine(thread, {
      turn_id: msg.turn_id,
      role: msg.role === "user" ? "user" : "system",
      text: msg.text,
    });
  }
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

async function refreshBranchPanel(root, sessionId) {
  const panel = root.querySelector("#chat-branch-panel");
  if (!panel || !sessionId) return;
  try {
    const graph = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/graph`);
    panel.replaceChildren();
    if (!graph.branches?.length) {
      applySiblingBadges(root, graph);
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    const title = document.createElement("h4");
    title.textContent = "Conversation branches";
    panel.appendChild(title);
    const list = document.createElement("ul");
    list.className = "chat-branch-list";
    for (const branch of graph.branches) {
      for (const childId of branch.child_turn_ids || []) {
        const node = (graph.nodes || []).find((n) => n.turn_id === childId);
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "linkish";
        btn.textContent = node?.text?.slice(0, 60) || childId;
        btn.dataset.testid = `maker-chat-branch-${childId}`;
        btn.addEventListener("click", async () => {
          const leaves = (graph.nodes || []).filter(
            (n) => !graph.edges?.some((e) => e.from_turn_id === n.turn_id),
          );
          const leaf = leaves.find((n) => {
            let cur = n.turn_id;
            while (cur) {
              if (cur === childId) return true;
              const edge = graph.edges?.find((e) => e.to_turn_id === cur);
              cur = edge?.from_turn_id;
            }
            return false;
          });
          if (!leaf) return;
          const updated = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/active-leaf`,
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ leaf_turn_id: leaf.turn_id }),
            },
          );
          renderMessagesFromSession(root, updated);
          await refreshBranchPanel(root, sessionId);
          toast("Switched branch", "success");
        });
        li.appendChild(btn);
        list.appendChild(li);
      }
    }
    panel.appendChild(list);
    applySiblingBadges(root, graph);
  } catch {
    panel.classList.add("hidden");
  }
}

async function startRunFromSession(sessionId, workType, root, projectId) {
  const message = root.querySelector("#chat-message")?.value?.trim() || "";
  const patchContext = attachmentFields(root);
  const dropdown = root.querySelector("#chat-work-type")?.value || "auto";
  const source = dropdown === "auto" ? "classifier" : "operator_override";

  const startPayload = {
    work_type: workType,
    work_type_source: source,
  };
  if (message) {
    startPayload.requirements = { business_prompt: message };
  }
  if (workType === "patch" && Object.keys(patchContext).length) {
    startPayload.patch_context = patchContext;
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
    renderTurnLine(thread, { ...body.turn, role: "system" });
  }
  window.location.hash = `/chat?run_id=${encodeURIComponent(runId)}`;
  toast(`${workTypeLabel(workType)} run started`, "success");
  root.querySelector("#chat-classifier-mount")?.replaceChildren();
  root.querySelector("#chat-message").value = "";
  return runId;
}

async function switchWorkType(root, sessionId, turnId, workType) {
  const updated = await apiJson(
    `/chat/sessions/${encodeURIComponent(sessionId)}/turns/${encodeURIComponent(turnId)}/switch-mode`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ work_type: workType }),
    },
  );
  const select = root.querySelector("#chat-work-type");
  if (select) select.value = workType;
  renderMessagesFromSession(root, updated);
  toast(`Mode: ${workTypeLabel(workType)}`, "success");
}

function applySiblingBadges(root, graph) {
  const thread = root.querySelector("#chat-thread");
  if (!thread || !graph?.nodes) return;
  for (const node of graph.nodes) {
    const siblings = Number(node.sibling_count || 0);
    if (siblings < 1) continue;
    const line = thread.querySelector(`[data-turn-id="${node.turn_id}"]`);
    if (!line || line.querySelector(".chat-sibling-badge")) continue;
    const badge = document.createElement("span");
    badge.className = "chat-sibling-badge muted";
    badge.dataset.testid = `maker-chat-sibling-badge-${node.turn_id}`;
    badge.textContent = `${siblings + 1} branches`;
    line.appendChild(badge);
  }
}

function appendThreadRunLine(root, text, { gateBlock = false } = {}) {
  const thread = root.querySelector("#chat-thread");
  if (!thread || !text) return;
  const li = document.createElement("li");
  li.className = "chat-thread-line chat-thread-line--theater";
  if (gateBlock) li.classList.add("chat-thread-line--gate-block");
  li.dataset.testid = gateBlock ? "maker-chat-gate-line" : "maker-chat-theater-line";
  li.textContent = String(text).slice(0, 500);
  thread.appendChild(li);
  const theaterLines = thread.querySelectorAll(".chat-thread-line--theater");
  while (theaterLines.length > THEATER_CAP) {
    theaterLines[0].remove();
  }
  thread.scrollTop = thread.scrollHeight;
  const archive = root.querySelector("#chat-theater-mount .chat-theater-lines");
  if (archive) {
    const copy = li.cloneNode(true);
    archive.appendChild(copy);
    while (archive.children.length > THEATER_CAP) {
      archive.removeChild(archive.firstChild);
    }
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
  }
  let escalationQueued = false;

  const onGateBlock = () => {
    if (escalationQueued) return;
    escalationQueued = true;
    maybeOfferPatchEscalation(root, runId, sessionId).catch(() => {});
    maybeOfferSliceCampaignPromotion(root, runId, sessionId, onStartRun).catch(() => {});
  };

  const handleTheaterPayload = (data) => {
    const text = theaterLineText(data);
    const gateBlock = data?.message_kind === "gate" && data?.severity === "block";
    if (text) appendThreadRunLine(root, text, { gateBlock });
    if (gateBlock) onGateBlock();
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
      const userTurn = [...thread.querySelectorAll("[data-turn-id]")].findLast(
        (el) => el.classList.contains("chat-thread-line--user"),
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

function mountAutopilotLadderHint(root) {
  if (localStorage.getItem(AUTOPILOT_LADDER_HINT_KEY) === "1") return;
  const hint = document.createElement("aside");
  hint.className = "panel chat-autopilot-hint";
  hint.dataset.testid = "maker-chat-autopilot-hint";
  const p = document.createElement("p");
  p.innerHTML =
    "<strong>Autonomy ladder (Nimble autopilot ~8):</strong> " +
    "Fix a bug (patch) → Build a feature (micro-slice) → Build an app (factory). " +
    "Chat offers escalation when a gate fails.";
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

export async function mountChat(root) {
  root.innerHTML = `
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
      <summary>Full run log (archive)</summary>
    </details>
    <ul id="chat-thread" class="chat-thread" data-testid="maker-chat-thread"></ul>
    <div id="chat-classifier-mount"></div>`;

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
  let lastClassification = null;
  let startPending = false;
  let theaterHandle = null;

  async function ensureSession(projectId) {
    if (!chatResumeEnabled()) {
      sessionId = "";
    }
    if (sessionId) {
      try {
        const existing = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`);
        if (existing.project_id === projectId) {
          renderMessagesFromSession(root, existing);
          await refreshBranchPanel(root, sessionId);
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
    return sessionId;
  }

  async function runStart(workType) {
    if (startPending || !sessionId) return;
    startPending = true;
    const startBtn = root.querySelector('[data-testid="maker-chat-start"]');
    if (startBtn) startBtn.disabled = true;
    try {
      const projectId = String(root.querySelector("#chat-project-select")?.value || "");
      const runId = await startRunFromSession(sessionId, workType, root, projectId);
      theaterHandle?.close();
      theaterHandle = bindChatTheaterForRun(root, runId, sessionId, (wt) => runStart(wt));
      await offerRunEscalations(runId);
    } catch (e) {
      toast(String(e.message || e), "error");
    } finally {
      startPending = false;
      if (startBtn) startBtn.disabled = false;
    }
  }

  root.querySelector("#chat-thread")?.addEventListener("chat-fork", async (ev) => {
    const turnId = ev.target?.closest("[data-turn-id]")?.dataset?.turnId;
    if (!turnId || !sessionId) return;
    try {
      const updated = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/fork`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ turn_id: turnId }),
      });
      renderMessagesFromSession(root, updated);
      await refreshBranchPanel(root, sessionId);
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
    theaterHandle?.close();
    theaterHandle = bindChatTheaterForRun(root, activeRunId, sessionId, (wt) => runStart(wt));
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
      const session = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`);
      renderMessagesFromSession(root, session);
      await refreshBranchPanel(root, sessionId);

      const classification = turnResp.classification || {};
      lastClassification = classification;

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
