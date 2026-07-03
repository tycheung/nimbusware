import { apiJson, toast } from "../api-client.js";
import { queueInterjection } from "../interjection-ribbon.js";
import { renderTurnLine } from "./chat_session_ui.js";
import { switchWorkType } from "./chat_work_type.js";

const ESCALATION_SLICE_OFFER =
  "Patch did not pass — widen to a micro-slice run? Switch work type to Slice or use Restore from here to branch.";

const ESCALATION_CAMPAIGN_OFFER =
  "Slice keeps replanning or failing — promote to an autonomous campaign for broader delivery?";
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
  await queueInterjection(runId, prefixed, "next");
  const thread = root.querySelector("#chat-thread");
  if (thread) {
    renderTurnLine(thread, { role: "system", text: "Steering queued for the active run." });
  }
  toast("Steering queued", "success");
}

export { maybeOfferPatchEscalation, maybeOfferSliceCampaignPromotion, steerActiveRun };
