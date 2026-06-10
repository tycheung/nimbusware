import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId, setActiveRun, syncRunIdToShell } from "../session-hub.js";

const WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];

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
  "Patch did not pass — widen to a micro-slice run? Use the Slice work type or type `[patch]` to retry a smaller fix.";

function appendThreadMessage(thread, { role, text, testId }) {
  const li = document.createElement("li");
  li.className = `chat-thread-line chat-thread-line--${role}`;
  if (testId) li.dataset.testid = testId;
  const label = document.createElement("strong");
  label.textContent = role === "user" ? "You" : "System";
  li.appendChild(label);
  li.appendChild(document.createTextNode(` ${text}`));
  thread.appendChild(li);
  thread.scrollTop = thread.scrollHeight;
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

  const signals = Array.isArray(classification.signals) ? classification.signals : [];
  if (signals.length) {
    const sigList = document.createElement("ul");
    sigList.className = "chat-signals";
    for (const sig of signals.slice(0, 5)) {
      const li = document.createElement("li");
      li.textContent = String(sig);
      sigList.appendChild(li);
    }
    card.appendChild(sigList);
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

  const thread = root.querySelector("#chat-thread");
  if (thread) {
    appendThreadMessage(thread, {
      role: "system",
      text: `Classifier suggests ${workTypeLabel(wt)}${classification.rationale ? ` — ${classification.rationale}` : ""}`,
      testId: "maker-chat-classifier-thread",
    });
  }
}

async function startRunFromSession(sessionId, workType, classification, root, projectId) {
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
  toast(`${workTypeLabel(workType)} run started`, "success");
  window.location.hash = `/progress?run_id=${encodeURIComponent(runId)}`;
}

async function maybeOfferPatchEscalation(root, runId) {
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
        const patchEff = meta.patch_effective;
        patchRun = wt === "patch" || (patchEff && patchEff.enabled);
      }
      const payload = ev.payload || {};
      const stage = String(payload.stage_name || "");
      if (stage === "slice.gate") {
        const verdict = String(meta.slice_gate_verdict || "").toUpperCase();
        if (verdict === "FAIL") patchFailed = true;
      }
      if (stage === "slice.verify" && meta.verify_ok === false) patchFailed = true;
    }
    if (!patchRun || !patchFailed) return;
    const thread = root.querySelector("#chat-thread");
    if (!thread) return;
    const prior = thread.querySelector('[data-testid="maker-chat-escalation-slice"]');
    if (prior) return;
    appendThreadMessage(thread, {
      role: "system",
      text: ESCALATION_SLICE_OFFER,
      testId: "maker-chat-escalation-slice",
    });
  } catch {
    /* advisory only */
  }
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
    appendThreadMessage(thread, {
      role: "system",
      text: "Steering queued for the active run.",
      testId: "maker-chat-steer-queued",
    });
  }
  toast("Steering queued", "success");
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
            data-testid="maker-chat-target-path" placeholder="src/foo.py (comma or newline separated)"></textarea>
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
      <button type="submit" class="primary" data-testid="maker-chat-start">Start</button>
    </form>
    <ul id="chat-thread" class="chat-thread" data-testid="maker-chat-thread"></ul>
    <div id="chat-classifier-mount"></div>`;

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

  let sessionId = "";
  let lastClassification = null;
  let startPending = false;

  async function runStart(workType) {
    if (startPending) return;
    startPending = true;
    const startBtn = root.querySelector('[data-testid="maker-chat-start"]');
    if (startBtn) startBtn.disabled = true;
    try {
      const projectId = String(root.querySelector("#chat-project-select")?.value || "");
      if (!projectId) {
        toast("Select a project", "error");
        return;
      }
      if (!sessionId) {
        const session = await apiJson("/chat/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: projectId }),
        });
        sessionId = String(session.session_id || session.id || "");
        if (!sessionId) throw new Error("Session response missing session_id");
      }
      await startRunFromSession(sessionId, workType, lastClassification, root, projectId);
    } catch (e) {
      toast(String(e.message || e), "error");
    } finally {
      startPending = false;
      if (startBtn) startBtn.disabled = false;
    }
  }

  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const activeRunId = params.get("run_id") || hashParams.get("run_id") || "";
  if (activeRunId) {
    await maybeOfferPatchEscalation(root, activeRunId);
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
      new URLSearchParams(window.location.search).get("run_id") ||
      new URLSearchParams(window.location.hash.split("?")[1] || "").get("run_id") ||
      "";
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

    const thread = root.querySelector("#chat-thread");
    if (thread) {
      appendThreadMessage(thread, { role: "user", text: message, testId: "maker-chat-user-thread" });
    }

    const dropdownWt = root.querySelector("#chat-work-type")?.value || "auto";
    const attachments = attachmentPayload(root);
    startPending = true;
    const startBtn = root.querySelector('[data-testid="maker-chat-start"]');
    if (startBtn) startBtn.disabled = true;

    try {
      const session = await apiJson("/chat/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
      });
      sessionId = String(session.session_id || session.id || "");
      if (!sessionId) throw new Error("Session response missing session_id");

      const classifyResp = await apiJson("/chat/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          project_id: projectId,
          message,
          attachments,
        }),
      });
      const classification = classifyResp.classification || classifyResp;
      lastClassification = classification;

      if (dropdownWt !== "auto") {
        await startRunFromSession(sessionId, dropdownWt, classification, root, projectId);
        return;
      }

      const suggested = String(classification.work_type || "slice");
      const confidence = Number(classification.confidence ?? 1);
      if (confidence >= 0.5) {
        renderClassifierCard(root, classification, {
          onAccept: (wt) => runStart(wt),
          onOverride: (wt) => {
            const select = root.querySelector("#chat-work-type");
            if (select) select.value = wt;
            runStart(wt);
          },
        });
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
      toast("Low confidence — confirm work type before starting", "info");
    } catch (e) {
      toast(String(e.message || e), "error");
    } finally {
      startPending = false;
      if (startBtn) startBtn.disabled = false;
    }
  });
}
