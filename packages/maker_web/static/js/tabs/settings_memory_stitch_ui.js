import { apiJson, toast } from "../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../broker_miss.js"; // sak499-b
import { getActiveProjectId, hydrateActiveRun, resolveRunId } from "../session-hub.js";

export async function wireMemoryLibraryPanel(root) {
  async function loadMemoryChunks() {
    const projectId = getActiveProjectId();
    const list = root.querySelector("#settings-memory-chunks");
    const caption = root.querySelector("#settings-memory-caption");
    if (!projectId) {
      if (caption) caption.textContent = "Select a project on Home to browse memory chunks.";
      list?.replaceChildren();
      return;
    }
    try {
      const body = await apiJson(
        `/memory/chunks?project_id=${encodeURIComponent(projectId)}&limit=50`,
      ).catch((e) => ({
        via: "broker_miss",
        error: String(e.message || e),
        feature: "memory_chunks",
        chunks: [],
      }));
      if (isDomainPeelMiss(body)) {
        toastIfMiss(body, toast, "Memory chunks unavailable");
        if (caption) {
          caption.textContent =
            formatDomainMissMessage(body, "Memory chunks unavailable") || "Memory chunks unavailable";
        }
        list?.replaceChildren();
        return;
      }
      if (caption) caption.textContent = body.caption || `${body.total || 0} chunks`;
      list?.replaceChildren();
      for (const ch of body.chunks || []) {
        const li = document.createElement("li");
        li.className = "memory-chunk-card";
        li.dataset.testid = "maker-settings-memory-chunk";
        li.innerHTML = `<strong>${ch.category || ch.source_event_type || "chunk"}</strong>
          <span class="muted">${ch.severity || ""} · run ${String(ch.run_id || "").slice(0, 8)}</span>
          <p class="memory-chunk-preview">${ch.excerpt || ""}</p>`;
        const insertBtn = document.createElement("button");
        insertBtn.type = "button";
        insertBtn.textContent = "Insert into active run";
        insertBtn.dataset.testid = "maker-settings-memory-insert";
        insertBtn.addEventListener("click", async () => {
          let runId = resolveRunId();
          if (!runId) runId = await hydrateActiveRun(apiJson);
          if (!runId) return toast("No active run — open Progress or start a build", "error");
          try {
            const res = await apiJson(
              `/runs/${encodeURIComponent(runId)}/memory-chunks/${encodeURIComponent(ch.chunk_id)}/insert`,
              { method: "POST" },
            );
            if (toastIfMiss(res, toast, "Memory chunk insert unavailable")) return;
            toast("Memory chunk inserted into run context", "success");
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        });
        li.appendChild(insertBtn);
        list?.appendChild(li);
      }
      if (!(body.chunks || []).length) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "No memory chunks indexed for this workspace yet.";
        list?.appendChild(li);
      }
    } catch (e) {
      toast(String(e.message || e), "error");
      if (caption) caption.textContent = String(e.message || e);
    }
  }
  root.querySelector("#settings-memory-refresh")?.addEventListener("click", () => {
    loadMemoryChunks().catch((e) => toast(String(e.message), "error"));
  });
  await loadMemoryChunks();
}

export async function wireStitchCatalogPanel(root) {
  let catalogVersion = 1;
  async function loadStitchCandidates() {
    const ul = root.querySelector("#settings-stitch-candidates");
    ul?.replaceChildren();
    try {
      const [candBody, catalogBody] = await Promise.all([
        apiJson("/bundles/catalog-candidates?limit=50").catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "catalog_candidates",
          candidates: [],
        })),
        apiJson("/bundles/catalog").catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "bundles_catalog",
        })),
      ]);
      if (toastIfMiss(candBody, toast, "Catalog candidates unavailable")) {
        const li = document.createElement("li");
        li.className = "muted";
        li.dataset.testid = "maker-settings-stitch-candidates-miss";
        li.textContent =
          formatDomainMissMessage(candBody, "Catalog candidates unavailable") ||
          "Catalog candidates unavailable";
        ul?.appendChild(li);
        return;
      }
      if (toastIfMiss(catalogBody, toast, "Bundles catalog unavailable")) {
        return;
      }
      catalogVersion = catalogBody.document_version ?? 1;
      for (const c of candBody.candidates || []) {
        const li = document.createElement("li");
        li.dataset.testid = "maker-settings-stitch-candidate";
        const label = `${c.candidate_id || c.id || "?"} (${c.run_id || "?"}) — ${c.status || "pending"}`;
        li.textContent = label;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Promote";
        btn.dataset.testid = "maker-settings-stitch-promote-one";
        btn.addEventListener("click", async () => {
          try {
            const res = await apiJson(
              `/bundles/catalog-candidates/${encodeURIComponent(c.run_id)}/${encodeURIComponent(c.candidate_id)}/promote?expected_version=${catalogVersion}`,
              { method: "POST" },
            );
            if (toastIfMiss(res, toast, "Catalog candidate promote unavailable")) return;
            toast("Candidate promoted", "success");
            await loadStitchCandidates();
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        });
        li.appendChild(btn);
        ul?.appendChild(li);
      }
      if (!(candBody.candidates || []).length) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = "No catalog candidates (admin token may be required).";
        ul?.appendChild(li);
      }
    } catch (e) {
      const li = document.createElement("li");
      li.className = "muted";
      li.textContent = String(e.message || e);
      ul?.appendChild(li);
    }
  }
  root.querySelector("#settings-stitch-refresh")?.addEventListener("click", () => {
    loadStitchCandidates().catch((e) => toast(String(e.message), "error"));
  });
  root.querySelector("#settings-stitch-batch")?.addEventListener("click", async () => {
    try {
      const res = await apiJson(
        `/bundles/catalog-candidates/promote-stitch-pending?expected_version=${catalogVersion}`,
        { method: "POST" },
      );
      if (toastIfMiss(res, toast, "Batch catalog promote unavailable")) return;
      toast("Batch promote complete", "success");
      await loadStitchCandidates();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
