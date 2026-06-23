import { wireHubNav } from "./models_hub_nav.js";
import { wireApiConnectionsPanel } from "./models_connections_ui.js";
import { wireLocalModelsPanel } from "./models_local_ui.js";

export async function mountModels(root) {
  root.dataset.testid = "maker-model-hub";
  root.innerHTML = `
    <header class="model-hub-header">
      <h2>Model Hub</h2>
      <nav class="model-hub-nav" aria-label="Model Hub sections">
        <button type="button" class="model-hub-nav-btn" data-section="local">Local models</button>
        <button type="button" class="model-hub-nav-btn" data-section="api-connections">API connections</button>
      </nav>
    </header>
    <section id="local" class="model-hub-section" data-testid="maker-model-hub-local">
      <h3>Local models</h3>
      <div id="models-ollama-status" class="models-ollama-status muted"></div>
      <div id="models-ollama-actions" class="actions"></div>
      <div id="models-installed-list"></div>
      <div id="models-hardware-strip" class="models-hardware-strip muted"></div>
      <div id="models-filter-bar" class="models-filter-bar">
        <label class="models-filter-item">
          <input type="checkbox" id="models-gpu-only" />
          GPU-only ranking (no CPU spill)
        </label>
        <label id="models-gpu-pool-wrap" class="models-filter-item" hidden>
          GPU pool
          <select id="models-gpu-pool"></select>
        </label>
      </div>
      <div id="models-wizard" class="wizard-panel">
        <p class="muted">Apply an Ollama preset to model routing in three steps.</p>
        <div id="models-step-1">
          <h4>1. Select model</h4>
          <table id="models-ranked-table" class="data-table">
            <thead><tr><th></th><th>Model</th><th>Fit</th><th></th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div id="models-step-2" hidden>
          <h4>2. Choose preset</h4>
          <div id="models-preset-cards"></div>
        </div>
        <div id="models-step-3" hidden>
          <h4>3. Confirm</h4>
          <p id="models-confirm-text"></p>
          <button type="button" id="models-apply-btn" class="primary">Apply preset</button>
          <button type="button" id="models-back-btn" class="secondary">Back</button>
        </div>
      </div>
      <form id="models-pull-form">
        <label>Pull model <input name="model" placeholder="llama3.2" required /></label>
        <button type="submit">Pull via Ollama</button>
      </form>
      <p id="models-pull-status"></p>
      <p id="models-catalog-info" class="muted"></p>
    </section>
    <section id="api-connections" class="model-hub-section" data-testid="maker-model-hub-api">
      <h3>API connections</h3>
      <p class="muted">Store API keys on this machine — secrets never appear in chat or audit exports.</p>
      <div id="models-api-cards" class="model-hub-api-cards"></div>
      <article class="model-hub-card model-hub-card--cursor" data-testid="maker-cursor-card">
        <h4>Cursor</h4>
        <p>Cursor Composer is IDE-only — use the MCP bridge for Nimbusware integration.</p>
        <a href="/docs/ide-bridge.md" target="_blank" rel="noopener">Open IDE bridge docs</a>
      </article>
    </section>`;

  wireHubNav(root);
  const local = wireLocalModelsPanel(root);
  await Promise.all([local.init(), wireApiConnectionsPanel(root)]);
}
