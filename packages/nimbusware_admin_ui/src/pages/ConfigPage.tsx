import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type BundleEntry = { id: string; title?: string | null; tags?: string[] };
type CatalogBody = {
  document_version?: number;
  authoritative?: string;
  bundles?: BundleEntry[];
  workflow_bundle_map?: Record<string, string>;
  faiss_index_ready?: boolean;
  faiss_index_stale?: boolean | null;
};
type CatalogSource = { authoritative?: string; path?: string };
type Candidate = { run_id?: string; candidate_id?: string; status?: string; summary?: string };

export function ConfigPage() {
  const [tab, setTab] = useState<"ollama" | "bundles" | "blast" | "personas" | "settings">("ollama");
  const [blastProfile, setBlastProfile] = useState("micro_slice");
  const [blastCaption, setBlastCaption] = useState("");
  const [blastRows, setBlastRows] = useState<
    { run_id: string; frozen: string; proposed: string }[]
  >([]);
  const [overlapRows, setOverlapRows] = useState<
    { business_area: string; development_role: string; overlap: string; count: string }[]
  >([]);
  const [overlapWarning, setOverlapWarning] = useState("");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [pullModel, setPullModel] = useState("");
  const [catalog, setCatalog] = useState<CatalogBody | null>(null);
  const [source, setSource] = useState<CatalogSource | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [mapProfile, setMapProfile] = useState("");
  const [mapBundleId, setMapBundleId] = useState("");
  const [newId, setNewId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newTags, setNewTags] = useState("");
  const [editTitles, setEditTitles] = useState<Record<string, string>>({});
  const [editTags, setEditTags] = useState<Record<string, string>>({});
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  const loadCatalog = useCallback(() => {
    apiJson<CatalogBody>("/bundles/catalog")
      .then((body) => {
        setCatalog(body);
        const titles: Record<string, string> = {};
        const tags: Record<string, string> = {};
        for (const b of body.bundles || []) {
          if (!b.id) continue;
          titles[b.id] = b.title || "";
          tags[b.id] = (b.tags || []).join(", ");
        }
        setEditTitles(titles);
        setEditTags(tags);
      })
      .catch((e) => setMsg(String((e as Error).message || e)));
    apiJson<CatalogSource>("/bundles/catalog/source")
      .then(setSource)
      .catch(() => setSource(null));
    apiJson<{ candidates?: Candidate[] }>("/bundles/catalog-candidates")
      .then((body) => setCandidates(body.candidates || []))
      .catch(() => setCandidates([]));
  }, []);

  useEffect(() => {
    if (tab === "ollama") {
      apiJson<{ models?: { name?: string }[] }>("/platform/ollama/models")
        .then((b) => setOllamaModels((b.models || []).map((m) => m.name || "").filter(Boolean)))
        .catch(() => setOllamaModels([]));
    }
    if (tab === "bundles" || tab === "blast") {
      loadCatalog();
    }
    if (tab === "settings") {
      apiJson<{ values?: Record<string, string> }>("/settings/system")
        .then((b) => setSettings(b.values || {}))
        .catch(() => setSettings({}));
    }
  }, [tab, loadCatalog]);

  const docVersion = catalog?.document_version ?? 1;

  async function patchBundle(bundleId: string) {
    try {
      await apiJson("/bundles/catalog/bundles/" + encodeURIComponent(bundleId), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: docVersion,
          title: editTitles[bundleId] || null,
          tags: (editTags[bundleId] || "")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        }),
      });
      setMsg(`Saved ${bundleId}`);
      loadCatalog();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function createBundle() {
    const id = newId.trim();
    if (!id) return;
    try {
      await apiJson("/bundles/catalog/bundles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: docVersion,
          entry: {
            id,
            title: newTitle.trim() || id,
            tags: newTags
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean),
          },
        }),
      });
      setNewId("");
      setNewTitle("");
      setNewTags("");
      setMsg(`Created ${id}`);
      loadCatalog();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function deleteBundle(bundleId: string) {
    try {
      await apiJson(
        `/bundles/catalog/bundles/${encodeURIComponent(bundleId)}?expected_version=${docVersion}`,
        { method: "DELETE" },
      );
      setMsg(`Deleted ${bundleId}`);
      loadCatalog();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function saveWorkflowMap() {
    const profile = mapProfile.trim();
    const bundleId = mapBundleId.trim();
    if (!profile || !bundleId) return;
    const nextMap = { ...(catalog?.workflow_bundle_map || {}), [profile]: bundleId };
    try {
      await apiJson("/bundles/catalog", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: docVersion,
          version: catalog?.version ?? 1,
          bundles: catalog?.bundles || [],
          workflow_bundle_map: nextMap,
        }),
      });
      setMsg(`Mapped ${profile} → ${bundleId}`);
      loadCatalog();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function promoteCandidate(runId: string, candidateId: string) {
    try {
      await apiJson(
        `/bundles/catalog-candidates/${encodeURIComponent(runId)}/${encodeURIComponent(candidateId)}/promote?expected_version=${docVersion}`,
        { method: "POST" },
      );
      setMsg(`Promoted ${candidateId}`);
      loadCatalog();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function pullOllama() {
    const model = pullModel.trim();
    if (!model) return;
    try {
      await apiJson("/admin/ollama/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      setMsg(`Pulled ${model}`);
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  async function saveSettings() {
    try {
      await apiJson("/settings/system", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: settings }),
      });
      setMsg("System settings saved");
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  return (
    <section>
      <h2>Configuration</h2>
      <nav class="sub-nav">
        <button type="button" class={tab === "ollama" ? "active" : ""} onClick={() => setTab("ollama")}>
          Ollama
        </button>
        <button type="button" class={tab === "bundles" ? "active" : ""} onClick={() => setTab("bundles")}>
          Bundles
        </button>
        <button type="button" class={tab === "blast" ? "active" : ""} onClick={() => setTab("blast")}>
          Blast radius
        </button>
        <button type="button" class={tab === "personas" ? "active" : ""} onClick={() => setTab("personas")}>
          Personas
        </button>
        <button type="button" class={tab === "settings" ? "active" : ""} onClick={() => setTab("settings")}>
          System settings
        </button>
      </nav>
      {msg ? <p class="hint">{msg}</p> : null}
      {tab === "ollama" ? (
        <div>
          <ul>
            {ollamaModels.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <label>
            Pull model{" "}
            <input value={pullModel} onInput={(e) => setPullModel((e.target as HTMLInputElement).value)} />
          </label>
          <button type="button" onClick={pullOllama}>
            Pull
          </button>
        </div>
      ) : null}
      {tab === "bundles" ? (
        <div>
          {source ? (
            <p class="muted">
              Authority: {source.authoritative || "unknown"}
              {source.path ? ` (${source.path})` : ""}
              {catalog ? ` · document version ${docVersion}` : ""}
              {catalog?.faiss_index_stale ? " · FAISS index stale" : ""}
            </p>
          ) : null}
          <button type="button" class="secondary" onClick={loadCatalog}>
            Refresh
          </button>
          <h3>Bundles</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Tags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(catalog?.bundles || []).map((b) => (
                <tr key={b.id}>
                  <td>{b.id}</td>
                  <td>
                    <input
                      value={editTitles[b.id] ?? ""}
                      onInput={(e) =>
                        setEditTitles({ ...editTitles, [b.id]: (e.target as HTMLInputElement).value })
                      }
                    />
                  </td>
                  <td>
                    <input
                      value={editTags[b.id] ?? ""}
                      onInput={(e) =>
                        setEditTags({ ...editTags, [b.id]: (e.target as HTMLInputElement).value })
                      }
                    />
                  </td>
                  <td>
                    <button type="button" onClick={() => patchBundle(b.id)}>
                      Save
                    </button>
                    <button type="button" class="secondary" onClick={() => deleteBundle(b.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h4>Add bundle</h4>
          <label>
            ID <input value={newId} onInput={(e) => setNewId((e.target as HTMLInputElement).value)} />
          </label>
          <label>
            Title <input value={newTitle} onInput={(e) => setNewTitle((e.target as HTMLInputElement).value)} />
          </label>
          <label>
            Tags (comma) <input value={newTags} onInput={(e) => setNewTags((e.target as HTMLInputElement).value)} />
          </label>
          <button type="button" onClick={createBundle}>
            Create
          </button>
          <h4>Workflow map</h4>
          <ul>
            {Object.entries(catalog?.workflow_bundle_map || {}).map(([profile, bundleId]) => (
              <li key={profile}>
                {profile} → {bundleId}
              </li>
            ))}
          </ul>
          <label>
            Profile <input value={mapProfile} onInput={(e) => setMapProfile((e.target as HTMLInputElement).value)} />
          </label>
          <label>
            Bundle id{" "}
            <input value={mapBundleId} onInput={(e) => setMapBundleId((e.target as HTMLInputElement).value)} />
          </label>
          <button type="button" onClick={saveWorkflowMap}>
            Add / update map
          </button>
          <h4>Promotion candidates</h4>
          {candidates.length === 0 ? (
            <p class="muted">No pending candidates.</p>
          ) : (
            <ul>
              {candidates.map((c, i) => {
                const rid = c.run_id || "";
                const cid = c.candidate_id || "";
                return (
                  <li key={`${rid}-${cid}-${i}`}>
                    {rid}/{cid} — {c.status || "pending"}
                    {c.summary ? ` — ${c.summary}` : ""}
                    {rid && cid && c.status !== "promoted" ? (
                      <button type="button" onClick={() => promoteCandidate(rid, cid)}>
                        Promote
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
      {tab === "blast" ? (
        <div>
          <h3>Workflow edit blast radius</h3>
          <p class="muted">
            Preview which recent runs would see different frozen gate settings if the workflow profile
            were materialized again.
          </p>
          <label>
            Workflow profile{" "}
            <select
              value={blastProfile}
              onChange={(e) => setBlastProfile((e.target as HTMLSelectElement).value)}
            >
              {Object.keys(catalog?.workflow_bundle_map || {}).length === 0 ? (
                <option value="micro_slice">micro_slice</option>
              ) : (
                Object.keys(catalog?.workflow_bundle_map || {}).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))
              )}
            </select>
          </label>
          <button type="button" onClick={() => void previewBlastRadius()}>
            Preview
          </button>
          {blastCaption ? <p class="hint">{blastCaption}</p> : null}
          {blastRows.length ? (
            <table class="data-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Frozen effective</th>
                  <th>Proposed effective</th>
                </tr>
              </thead>
              <tbody>
                {blastRows.map((row) => (
                  <tr key={row.run_id}>
                    <td>
                      {row.run_id ? (
                        <a href={`/v1/admin/app/runs/${row.run_id}`}>{row.run_id}</a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <code>{row.frozen}</code>
                    </td>
                    <td>
                      <code>{row.proposed}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}
      {tab === "personas" ? (
        <div>
          <h3>Scope overlap report</h3>
          <p class="muted">
            Business area × development role pairs with overlapping <code>scope_in</code> tags from
            the persona shelf.
          </p>
          {overlapWarning ? <p class="error">{overlapWarning}</p> : null}
          {overlapRows.length ? (
            <table class="data-table">
              <thead>
                <tr>
                  <th>Business area</th>
                  <th>Development role</th>
                  <th>Overlap tags</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {overlapRows.map((row, i) => (
                  <tr key={i}>
                    <td>{row.business_area}</td>
                    <td>{row.development_role}</td>
                    <td>{row.overlap}</td>
                    <td>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p class="muted">No overlapping scope_in pairs in the current shelf.</p>
          )}
        </div>
      ) : null}
      {tab === "settings" ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void saveSettings();
          }}
        >
          {Object.entries(settings).map(([k, v]) => (
            <label key={k}>
              {k}{" "}
              <input
                value={v}
                onInput={(e) =>
                  setSettings((s) => ({ ...s, [k]: (e.target as HTMLInputElement).value }))
                }
              />
            </label>
          ))}
          <button type="submit">Save</button>
        </form>
      ) : null}
    </section>
  );
}
