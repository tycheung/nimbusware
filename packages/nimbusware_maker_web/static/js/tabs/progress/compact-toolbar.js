import { apiJson, toast } from "../../api-client.js";
import { resolveRunId } from "../../session-hub.js";
import { maybeRegisterPushSubscription } from "../../app-shell.js";
import { renderCompactionPreview } from "./render-chips.js";

async function compactRun(body) {
  const rid = resolveRunId();
  if (!rid) return;
  try {
    await apiJson(`/runs/${encodeURIComponent(rid)}/compact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    toast("Context compacted", "success");
  } catch (e) {
    toast(String(e.message || e), "error");
  }
}

export function wireMobilePushPanel() {
  const panel = document.getElementById("mobile-push-panel");
  const status = document.getElementById("mobile-push-status");
  const btn = document.getElementById("mobile-push-enable");
  if (!panel || !document.body.classList.contains("mobile-mode")) return;
  panel.hidden = false;
  if (status) {
    if (!("Notification" in window)) {
      status.textContent = "Notifications not supported in this browser.";
      btn?.setAttribute("disabled", "disabled");
      return;
    }
    status.textContent =
      Notification.permission === "granted"
        ? "Push enabled for this device (tap to re-register for active run)."
        : "Get notified when campaign milestones complete.";
  }
  btn?.addEventListener("click", async () => {
    const ok = await maybeRegisterPushSubscription();
    toast(ok ? "Push notifications enabled" : "Could not enable push", ok ? "success" : "error");
    if (ok && status) status.textContent = "Push registered for active run.";
  });
}

export function wireCompactToolbar() {
  const bar = document.getElementById("compact-toolbar");
  if (!bar) return;
  bar.hidden = false;
  document.getElementById("compact-all-btn")?.addEventListener("click", () => compactRun({ scope: "all" }));
  document.getElementById("compact-last-n-btn")?.addEventListener("click", () => {
    const n = Number(document.getElementById("compact-last-n")?.value || 3);
    compactRun({ scope: "last_n", n });
  });
  document.getElementById("compact-selected-btn")?.addEventListener("click", () => {
    const refs = [...document.querySelectorAll("#theater-list input[data-theater-pick]:checked")]
      .map((el) => el.getAttribute("data-store-seq"))
      .filter(Boolean);
    if (!refs.length) {
      toast("Select theater messages first", "error");
      return;
    }
    compactRun({ scope: "source_refs", source_refs: refs });
  });
  document.getElementById("compact-revert-btn")?.addEventListener("click", async () => {
    const rid = resolveRunId();
    if (!rid) return;
    try {
      const budget = await apiJson(`/runs/${encodeURIComponent(rid)}/maker-progress`);
      const last = budget?.context_budget?.last_compaction;
      const cid = last?.compaction_id;
      if (!cid) {
        toast("No compaction to revert", "error");
        return;
      }
      const preview = String(last?.summary || "").slice(0, 400);
      const tokens =
        last?.tokens_before != null && last?.tokens_after != null
          ? `${last.tokens_before}→${last.tokens_after} tok`
          : "";
      const msg = [
        "Revert last compaction?",
        tokens,
        preview ? `\n\n${preview}${last.summary?.length > 400 ? "…" : ""}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      if (!window.confirm(msg)) return;
      await apiJson(`/runs/${encodeURIComponent(rid)}/compactions/${encodeURIComponent(cid)}/revert`, {
        method: "POST",
      });
      toast("Compaction reverted", "success");
      renderCompactionPreview(null);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  document.getElementById("compact-save-artifact-btn")?.addEventListener("click", async () => {
    const rid = resolveRunId();
    if (!rid) return;
    try {
      const out = await apiJson(`/runs/${encodeURIComponent(rid)}/context-artifacts/from-compaction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      toast(`Saved artifact ${out.title || out.artifact_id}`, "success");
      const timeline = await apiJson(`/runs/${encodeURIComponent(rid)}/timeline?limit=1`);
      const created = (timeline.events || []).find((e) => e.event_type === "run.created");
      const projectId = created?.metadata?.project?.id;
      if (projectId) {
        const { renderContextArtifacts } = await import("./context-panels.js");
        await renderContextArtifacts(projectId);
      }
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
