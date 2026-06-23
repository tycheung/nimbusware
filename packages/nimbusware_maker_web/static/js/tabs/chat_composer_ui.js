import { apiJson, toast } from "../api-client.js";
import {
  defaultAutopilotProfileId,
  defaultEnforcementProfileId,
} from "../operator-default-profiles.js";
import { setActiveProjectId, setActiveRun, syncRunIdToShell } from "../session-hub.js";
import { ensureRunCard } from "./chat_theater_ui.js";
import { renderTurnLine, workTypeLabel } from "./chat_thread_ui.js";

const WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];
const AUTOPILOT_LADDER_HINT_KEY = "maker_chat_autopilot_ladder_dismissed";
const RESUME_KEY = "maker_chat_resume_session";

function chatResumeEnabled() {
  const raw = localStorage.getItem(RESUME_KEY);
  return raw == null || raw === "1" || raw === "true";
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
  const enforcementProfileId = defaultEnforcementProfileId();
  if (enforcementProfileId) startPayload.enforcement_profile_id = enforcementProfileId;
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

function mountAutopilotLadderHint(root) {
  if (localStorage.getItem(AUTOPILOT_LADDER_HINT_KEY) === "1") return;
  if (root.querySelector("[data-testid='maker-chat-autopilot-hint']")) return;
  const hint = document.createElement("aside");
  hint.className = "panel chat-autopilot-hint";
  hint.dataset.testid = "maker-chat-autopilot-hint";
  const trustLevel = root.querySelector("[data-autopilot-slider]")?.value || "8";
  const enforceLevel = root.querySelector("[data-enforcement-slider]")?.value || "5";
  const p = document.createElement("p");
  p.innerHTML =
    `<strong>Operator ladder</strong> — ` +
    `Trust ~${trustLevel} (autonomy): Fix a bug (patch) → Build a feature (slice) → Build an app (factory). ` +
    `Enforcement ~${enforceLevel} (CI depth): light checks for fixes (~4), full slice gates (~5), ship parity (~7+). ` +
    "Adjust both sliders in the ribbon when a run is active.";
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

export {
  attachmentFields,
  attachmentPayload,
  chatResumeEnabled,
  mountAutopilotLadderHint,
  renderClassifierCard,
  startRunFromSession,
};
