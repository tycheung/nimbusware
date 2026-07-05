import { apiJson, toast } from "./api-client.js";
import { loadPlatformUserProfiles, populateProfileSelect, ribbonControl } from "./ribbon-shared.js";

export async function loadStandardsRegistry() {
  return apiJson("/standards/registry");
}

export async function loadStandardsUserProfiles() {
  return loadPlatformUserProfiles(apiJson, "/users/me/standards-profile");
}

export function applyStandardsProfileToControls(root, profile) {
  const facadeSelect = ribbonControl(root, "data-standards-facade", "standards-facade-select");
  const summary = ribbonControl(root, "data-standards-summary", "standards-summary");
  if (facadeSelect && profile.facade_id) facadeSelect.value = profile.facade_id;
  if (summary) {
    const bundles = (profile.bundle_ids || []).join(", ") || "none";
    summary.textContent = `${profile.facade_id || "custom"} · ${bundles}`;
  }
}

export async function wireStandardsRibbon(root, runId) {
  const facadeSelect = ribbonControl(root, "data-standards-facade", "standards-facade-select");
  const bundleSelect = ribbonControl(root, "data-standards-bundles", "standards-bundles-select");
  const summary = ribbonControl(root, "data-standards-summary", "standards-summary");
  const profileSelect = ribbonControl(root, "data-standards-profile-select", "standards-profile-select");
  if (!runId) return;

  let registry = { facades: {}, bundles: {} };
  try {
    registry = await loadStandardsRegistry();
  } catch {
    /* registry optional when platform disabled */
  }

  if (facadeSelect) {
    facadeSelect.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "— pick facade —";
    facadeSelect.appendChild(empty);
    for (const [id, meta] of Object.entries(registry.facades || {})) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = meta.display_name || id;
      facadeSelect.appendChild(opt);
    }
  }

  if (bundleSelect) {
    bundleSelect.replaceChildren();
    for (const [id, meta] of Object.entries(registry.bundles || {})) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = meta.display_name || id;
      bundleSelect.appendChild(opt);
    }
  }

  const profiles = await loadStandardsUserProfiles();
  populateProfileSelect(profileSelect, profiles);
  profileSelect?.addEventListener("change", (ev) => {
    const pid = ev.target?.value;
    if (!pid) return;
    const match = profiles.find((p) => p.profile_id === pid);
    if (match) applyStandardsProfileToControls(root, match);
  });

  ribbonControl(root, "data-standards-save", "standards-save-btn")?.addEventListener(
    "click",
    async () => {
      const facadeId = facadeSelect?.value || null;
      const bundles = bundleSelect
        ? Array.from(bundleSelect.selectedOptions).map((o) => o.value)
        : [];
      try {
        const body = await apiJson(`/runs/${encodeURIComponent(runId)}/standards`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ facade_id: facadeId, bundles }),
        });
        toast("Standards profile applied", "success");
        if (summary) {
          const eff = body.standards_effective || {};
          const bundleLabel = (eff.bundle_ids || []).join(", ") || "none";
          summary.textContent = `${eff.facade_id || "custom"} · ${bundleLabel}`;
        }
        root.dispatchEvent(new CustomEvent("standards-updated", { detail: body }));
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    },
  );

  ribbonControl(root, "data-standards-run", "standards-run-btn")?.addEventListener(
    "click",
    async () => {
      try {
        const body = await apiJson(`/runs/${encodeURIComponent(runId)}/standards/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        const results = body.results || [];
        const failed = results.filter((r) => r && r.passed === false).length;
        toast(failed ? `Standards run: ${failed} bundle(s) failed` : "Standards run passed", failed ? "error" : "success");
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    },
  );

  try {
    const current = await apiJson(`/runs/${encodeURIComponent(runId)}/standards`);
    applyStandardsProfileToControls(root, current.standards_effective || {});
  } catch {
    if (summary) summary.textContent = "";
  }
}

export function standardsRibbonHtml({ compact = false, rootId = "" } = {}) {
  const tag = compact ? "div" : "section";
  const idAttr = rootId ? ` id="${rootId}"` : "";
  const panelClass = compact ? "" : " panel";
  return `
    <${tag}${idAttr} class="standards-ribbon${panelClass}${compact ? " standards-ribbon--compact" : ""}" data-testid="maker-standards-ribbon">
      <h4>Standards profile</h4>
      <label>Facade
        <select data-standards-facade data-testid="maker-standards-facade"></select>
      </label>
      <label>Bundles
        <select data-standards-bundles multiple size="4" data-testid="maker-standards-bundles"></select>
      </label>
      <p class="muted" data-standards-summary data-testid="maker-standards-summary"></p>
      <div class="actions">
        <label>Saved profile
          <select data-standards-profile-select data-testid="maker-standards-profile-select">
            <option value="">— custom —</option>
          </select>
        </label>
        <button type="button" data-standards-save data-testid="maker-standards-save">Apply to run</button>
        <button type="button" data-standards-run data-testid="maker-standards-run">Run now</button>
      </div>
    </${tag}>`;
}
