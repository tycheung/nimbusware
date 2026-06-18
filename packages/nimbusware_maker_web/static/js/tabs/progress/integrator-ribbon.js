import { apiJson, toast } from "../../api-client.js";

let stitchCatalogVersion = 1;

export async function renderIntegratorRibbon(runId) {
  const panel = document.getElementById("integrator-ribbon");
  const bodyEl = document.getElementById("integrator-ribbon-body");
  if (!panel || !bodyEl || !runId) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=1`);
    const ig = timeline.integrator_gate;
    const delta = timeline.integrator_gate_delta;
    const parts = [];
    if (ig && ig.verdict) parts.push(`Integrator gate: ${ig.verdict}`);
    if (delta && delta.summary) parts.push(String(delta.summary));
    if (!parts.length) {
      bodyEl.textContent = "No integrator gate summary yet.";
      return;
    }
    bodyEl.textContent = parts.join(" · ");
  } catch {
    bodyEl.textContent = "Integrator summary unavailable.";
  }
}

export async function refreshStitchFromProgress() {
  try {
    const catalogBody = await apiJson("/bundles/catalog").catch(() => ({ document_version: 1 }));
    stitchCatalogVersion = catalogBody.document_version ?? 1;
    const candBody = await apiJson("/bundles/catalog-candidates?limit=20");
    const pending = (candBody.candidates || []).filter((c) => (c.status || "pending") === "pending");
    const bodyEl = document.getElementById("integrator-ribbon-body");
    if (bodyEl && pending.length) {
      bodyEl.textContent = `${bodyEl.textContent ? `${bodyEl.textContent} · ` : ""}${pending.length} stitch candidate(s) pending`;
    }
  } catch {
    /* ignore */
  }
}

export function wireIntegratorRibbon() {
  document.getElementById("integrator-stitch-refresh")?.addEventListener("click", () => {
    refreshStitchFromProgress().catch((e) => toast(String(e.message || e), "error"));
  });
  document.getElementById("integrator-stitch-promote-batch")?.addEventListener("click", async () => {
    try {
      await apiJson(
        `/bundles/catalog-candidates/promote-stitch-pending?expected_version=${stitchCatalogVersion}`,
        { method: "POST" },
      );
      toast("Stitch batch promote complete", "success");
      await refreshStitchFromProgress();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
