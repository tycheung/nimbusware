/** Progress tab mount HTML (injected once on mount). */
import { autopilotRibbonHtml } from "../../autopilot-ribbon.js";
import { enforcementRibbonHtml } from "../../enforcement-ribbon.js";
import { interjectionRibbonHtml } from "../../interjection-ribbon.js";

const ENFORCEMENT_RIBBON = enforcementRibbonHtml({ rootId: "enforcement-ribbon" });
const AUTOPILOT_RIBBON = autopilotRibbonHtml({ rootId: "autopilot-ribbon" });
const INTERJECTION_RIBBON = interjectionRibbonHtml({ rootId: "interjection-ribbon" });

export const PROGRESS_MOUNT_HTML = `
      <div id="compact-toolbar" class="actions" data-testid="maker-compact-toolbar" hidden>
        <button type="button" id="compact-all-btn">Compact all</button>
        <label>Last N <input type="number" id="compact-last-n" min="1" max="50" value="3" style="width:3rem" /></label>
        <button type="button" id="compact-last-n-btn">Compact last N</button>
        <button type="button" id="compact-selected-btn">Compact selected</button>
        <button type="button" id="compact-save-artifact-btn" data-testid="maker-compact-save-artifact">Save compaction as artifact</button>
        <button type="button" id="compact-revert-btn">Revert last compaction</button>
      </div>
      <section id="compaction-preview" class="compaction-preview panel" data-testid="maker-compaction-preview" hidden>
        <h4>Last compaction</h4>
        <p id="compaction-preview-meta" class="muted" data-testid="maker-compaction-preview-meta"></p>
        <pre id="compaction-preview-summary" class="compaction-summary-pre" hidden data-testid="maker-compaction-preview-summary"></pre>
        <button type="button" id="compaction-preview-toggle" class="linkish" data-testid="maker-compaction-preview-toggle">Show summary</button>
      </section>
      <section id="mobile-push-panel" class="panel mobile-only-panel" data-testid="maker-mobile-push-panel" hidden>
        <h4>Run notifications</h4>
        <p id="mobile-push-status" class="muted" data-testid="maker-mobile-push-status"></p>
        <button type="button" id="mobile-push-enable" data-testid="maker-mobile-push-enable">Enable push notifications</button>
      </section>
      <section id="integrator-ribbon" class="panel integrator-ribbon" data-testid="maker-integrator-ribbon">
        <h4>Integrator &amp; stitch</h4>
        <p id="integrator-ribbon-body" class="muted"></p>
        <div class="actions">
          <button type="button" id="integrator-stitch-refresh" data-testid="maker-integrator-stitch-refresh">Refresh stitch candidates</button>
          <button type="button" id="integrator-stitch-promote-batch" data-testid="maker-integrator-stitch-promote-batch">Promote pending batch</button>
        </div>
      </section>
      <section id="dev-env-ribbon" class="panel" data-testid="maker-dev-env-ribbon">
        <h4>Dev environment</h4>
        <p id="dev-env-status-body" class="muted"></p>
        <p id="dev-env-regression-detail" class="muted" data-testid="maker-dev-env-regression-detail"></p>
        <div class="actions">
          <button type="button" id="dev-env-start-btn" data-testid="maker-dev-env-start">Start session</button>
          <button type="button" id="dev-env-stop-btn" data-testid="maker-dev-env-stop">Stop session</button>
          <button type="button" id="dev-env-regression-btn" data-testid="maker-dev-env-regression">Run regression</button>
        </div>
      </section>
      ${INTERJECTION_RIBBON}
      ${ENFORCEMENT_RIBBON}
      ${AUTOPILOT_RIBBON}
      <section id="learnings-ribbon" class="panel" data-testid="maker-learnings-ribbon">
        <h4>Learnings</h4>
        <p id="stitch-suggestion" class="hint" hidden data-testid="maker-stitch-suggestion"></p>
        <ul id="learnings-list" data-testid="maker-learnings-list"></ul>
      </section>
      <section id="variant-ribbon" class="panel" data-testid="maker-variant-ribbon">
        <h4>Variant arena</h4>
        <p id="variant-body" class="muted" data-testid="maker-variant-body">No variant experiments yet</p>
        <ul id="variant-list" class="variant-list" data-testid="maker-variant-list"></ul>
      </section>
      <section id="council-ribbon" class="panel" data-testid="maker-council-ribbon" hidden>
        <h4>Improvement council</h4>
        <p id="council-body" class="muted"></p>
      </section>
      <ul id="theater-list"></ul>
      <p id="pressure-banner" class="pressure-banner" hidden></p>
      <span id="work-type-badge" class="work-type-badge" hidden data-testid="maker-work-type-badge"></span>
      <span id="context-budget-chip" class="context-budget-chip" hidden></span>
      <p id="factory-status-chip" class="factory-status-chip" hidden data-testid="maker-factory-status"></p>
      <p id="enforcement-chip" class="enforcement-chip" hidden data-testid="maker-enforcement-chip"></p>
      <p id="gate-summary-banner" class="gate-summary-banner" hidden></p>
      <span id="role-cost-chip" class="role-cost-chip" hidden></span>
      <p id="handoff-preview" class="handoff-preview" hidden></p>
      <p id="slice-summary"></p>
      <p id="campaign-controls" class="actions" hidden></p>
      <ol id="slice-list"></ol>
      <section id="completion-cockpit" class="completion-cockpit panel" data-testid="maker-completion-cockpit" hidden>
        <h4>Completion</h4>
        <p id="completion-terminal" data-testid="maker-completion-terminal"></p>
        <p id="completion-rationale" class="muted" data-testid="maker-completion-rationale"></p>
        <ul id="completion-blocking" data-testid="maker-completion-blocking"></ul>
        <div class="actions">
          <a id="completion-rubric-link" href="#/review" data-testid="maker-completion-rubric-link">Launch rubric (Review)</a>
          <button type="button" id="completion-run-launch-check" data-testid="maker-completion-run-launch-check">Run launch check</button>
        </div>
        <div id="completion-launch-scorecard" class="launch-scorecard" data-testid="maker-completion-launch-scorecard"></div>
      </section>
      <section id="critic-reliability-panel" class="panel" data-testid="maker-critic-reliability-panel" hidden>
        <h4>Critic reliability</h4>
        <div id="critic-reliability-mount"></div>
      </section>
      <section id="findings-workspace" class="findings-workspace" data-testid="maker-findings-workspace">
        <h4>Gate failures &amp; findings</h4>
        <div id="gate-fail-steps" class="gate-fail-steps" hidden data-testid="maker-gate-fail-steps"></div>
        <ul id="findings-list"></ul>
      </section>
      <h4>Context artifacts</h4>
      <p class="actions">
        <a href="#/settings" data-testid="maker-progress-memory-library-link">Memory library (Settings)</a>
      </p>
      <ul id="context-artifacts-list" class="context-artifacts-list"></ul>
      <h4>Memory influence</h4>
      <table id="memory-influence-table" data-testid="maker-memory-influence-table"><thead><tr><th>Stage</th><th>Hits</th><th>Digest</th></tr></thead><tbody></tbody></table>`;
