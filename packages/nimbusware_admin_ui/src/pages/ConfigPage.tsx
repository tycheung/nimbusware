import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

export function ConfigPage() {
  const [tab, setTab] = useState<"ollama" | "bundles" | "settings">("ollama");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [pullModel, setPullModel] = useState("");
  const [bundles, setBundles] = useState<Record<string, unknown>[]>([]);
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (tab === "ollama") {
      apiJson<{ models?: { name?: string }[] }>("/platform/ollama/models")
        .then((b) => setOllamaModels((b.models || []).map((m) => m.name || "").filter(Boolean)))
        .catch(() => setOllamaModels([]));
    }
    if (tab === "bundles") {
      apiJson<{ bundles?: Record<string, unknown>[] }>("/bundles/catalog")
        .then((b) => setBundles(b.bundles || []))
        .catch(() => setBundles([]));
    }
    if (tab === "settings") {
      apiJson<{ values?: Record<string, string> }>("/settings/system")
        .then((b) => setSettings(b.values || {}))
        .catch(() => setSettings({}));
    }
  }, [tab]);

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
        <ul>
          {bundles.map((b, i) => (
            <li key={i}>{String(b.id || b.bundle_id || JSON.stringify(b).slice(0, 80))}</li>
          ))}
        </ul>
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
