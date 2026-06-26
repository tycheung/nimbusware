export function settingsShellHtml() {
  return `
    <section id="governor-panel" class="panel">
      <h3>Resource governor</h3>
      <p id="governor-hardware-summary" class="muted"></p>
      <form id="governor-form">
        <label>
          Max system RAM %
          <input type="range" id="gov-ram-pct" name="NIMBUSWARE_MAX_SYSTEM_RAM_PCT" min="50" max="95" step="1" />
          <span id="gov-ram-pct-val"></span>
        </label>
        <label>
          Max VRAM %
          <input type="range" id="gov-vram-pct" name="NIMBUSWARE_MAX_VRAM_PCT" min="50" max="95" step="1" />
          <span id="gov-vram-pct-val"></span>
        </label>
        <label>
          <input type="checkbox" id="gov-auto-adjust" name="NIMBUSWARE_HW_AUTO_ADJUST" />
          Auto-adjust limits to detected hardware tier
        </label>
        <p id="governor-preview" class="muted"></p>
        <button type="submit" class="primary">Save governor</button>
      </form>
    </section>
    <form id="settings-form"></form>
    <section id="settings-launch-check" class="launch-panel">
      <h3>Launch readiness</h3>
      <p class="muted" id="settings-launch-run-hint" data-testid="maker-settings-launch-run-hint"></p>
      <div class="actions">
        <button type="button" id="settings-run-launch-eval" data-testid="maker-settings-run-launch-eval">Run launch check</button>
      </div>
      <div id="settings-launch-scorecard" class="launch-scorecard" data-testid="maker-settings-launch-scorecard"></div>
    </section>
    <section id="settings-collab" class="panel" data-testid="maker-settings-collab" hidden>
      <h3>Collaborative chat</h3>
      <p class="muted">Enable multi-user sessions without editing .env.</p>
      <label>
        <input type="checkbox" id="settings-collab-enabled" data-testid="maker-settings-collab-enabled" />
        Collaborative chat enabled
      </label>
    </section>
    <section id="settings-compute-sharing" class="panel" data-testid="maker-settings-compute-sharing">
      <h3>Compute sharing</h3>
      <p class="muted">Distributed mesh defaults for collaborative sessions.</p>
      <label>
        <input type="checkbox" id="settings-compute-default-share" data-testid="maker-settings-compute-default-share" />
        Default when joining others' sessions: share my compute
      </label>
      <label>
        Default workload mode for new sessions
        <select id="settings-compute-workload-mode" data-testid="maker-settings-compute-workload-mode">
          <option value="host_only">Host only</option>
          <option value="manual_claim" selected>Manual claim</option>
          <option value="auto_share">Auto share</option>
          <option value="auto_optimize">Auto optimize</option>
        </select>
      </label>
      <label>
        Scheduling policy (auto share / optimize)
        <select id="settings-compute-spread-policy" data-testid="maker-settings-compute-spread-policy">
          <option value="spread" selected>Spread</option>
          <option value="pack">Pack</option>
        </select>
      </label>
    </section>
    <section id="settings-optimizer-weights" class="panel" data-testid="maker-settings-optimizer-weights">
      <h3>Auto-optimize weights</h3>
      <p class="muted">Priority mix when workload mode is Auto optimize (fo1788).</p>
      <div id="settings-optimizer-fields"></div>
      <div class="actions">
        <button type="button" id="settings-optimizer-save" class="secondary" data-testid="maker-settings-optimizer-save">
          Save weights
        </button>
      </div>
    </section>
    <section id="settings-agent-models" class="panel" data-testid="maker-settings-agent-models">
      <h3>Agent &amp; Models</h3>
      <p class="muted">
        Per-role provider bindings. API keys are configured in
        <a href="#/models?section=api-connections">Model Hub → API connections</a>.
      </p>
      <div id="settings-agent-models-table"></div>
      <div class="actions">
        <button type="button" id="settings-agent-models-save" class="primary" data-testid="maker-settings-agent-models-save">
          Save bindings
        </button>
      </div>
    </section>
    <section id="settings-routing-panel" class="panel" data-testid="maker-settings-routing-presets">
      <h3>Hybrid model routing</h3>
      <p class="muted" id="settings-routing-active" data-testid="maker-settings-routing-active"></p>
      <label>
        Preset
        <select id="settings-routing-select" data-testid="maker-settings-routing-select"></select>
      </label>
      <p class="muted" id="settings-routing-cloud" data-testid="maker-settings-routing-cloud"></p>
      <button type="button" id="settings-routing-apply" class="primary" data-testid="maker-settings-routing-apply">
        Apply routing preset
      </button>
    </section>
    <section id="settings-chat-panel" class="panel" data-testid="maker-settings-chat-panel">
      <h3>Chat</h3>
      <label>
        <input type="checkbox" id="settings-chat-resume" data-testid="maker-settings-chat-resume" />
        Resume last chat session when opening the Chat tab
      </label>
    </section>
    <section id="settings-trust-panel" class="panel" data-testid="maker-settings-trust-panel">
      <h3>Trust / Autopilot defaults</h3>
      <p class="muted">Patch runs default to Nimble (8); factory runs default to Continuous improve (10). Saved profile overrides at Chat start.</p>
      <label>
        Default saved profile
        <select id="settings-default-autopilot-profile" data-testid="maker-settings-default-autopilot-profile">
          <option value="">— none —</option>
        </select>
      </label>
    </section>
    <section id="settings-enforcement-panel" class="panel" data-testid="maker-settings-enforcement-panel">
      <h3>Enforcement depth defaults</h3>
      <p class="muted">Saved enforcement profile applied at Chat run start (orthogonal to trust/autopilot).</p>
      <label>
        Default saved profile
        <select id="settings-default-enforcement-profile" data-testid="maker-settings-default-enforcement-profile">
          <option value="">— none —</option>
        </select>
      </label>
    </section>
    <section id="settings-memory-library" class="panel" data-testid="maker-settings-memory-library">
      <h3>Memory library</h3>
      <p class="muted" id="settings-memory-caption"></p>
      <button type="button" id="settings-memory-refresh" data-testid="maker-settings-memory-refresh">Refresh chunks</button>
      <ul id="settings-memory-chunks" class="memory-chunk-list"></ul>
    </section>
    <section id="settings-stitch-panel" class="panel" data-testid="maker-settings-stitch-panel">
      <h3>Stitch / catalog integrator</h3>
      <p class="muted">Promote research catalog candidates into the bundle catalog (requires admin token).</p>
      <button type="button" id="settings-stitch-refresh" data-testid="maker-settings-stitch-refresh">Load candidates</button>
      <button type="button" id="settings-stitch-batch" data-testid="maker-settings-stitch-batch-promote">Promote pending stitch batch</button>
      <ul id="settings-stitch-candidates"></ul>
    </section>
    <section id="settings-critic-reliability" class="panel" data-testid="maker-settings-critic-reliability">
      <h3>Critic reliability</h3>
      <div id="settings-critic-mount"></div>
      <details class="persona-probation-details">
        <summary>Persona probation metrics</summary>
        <label>Shelf <input type="text" id="settings-critic-shelf" value="development" /></label>
        <label>Persona ID <input type="text" id="settings-critic-persona" placeholder="persona id" /></label>
        <button type="button" id="settings-critic-probation" data-testid="maker-settings-critic-probation">Load probation reliability</button>
        <pre id="settings-critic-probation-body" class="json-pre"></pre>
      </details>
    </section>
    <p class="muted" id="reresearch-help">
      <strong>Re-research on plan fail</strong> (<code>NIMBUSWARE_RERESARCH_MISSING_CONTEXT</code>):
      when enabled, the pipeline may re-run research after planner missing-context failures.
    </p>`;
}
