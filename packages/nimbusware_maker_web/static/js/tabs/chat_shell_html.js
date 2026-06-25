import { autopilotRibbonHtml } from "../autopilot-ribbon.js";
import { enforcementRibbonHtml } from "../enforcement-ribbon.js";
import { chatInterjectionRibbonHtml } from "../interjection-ribbon.js";
import { isSafeCodingUx } from "../safe-coding-ux.js";
import { workTypeLabel } from "./chat_thread_ui.js";

export const CHAT_WORK_TYPES = ["auto", "patch", "slice", "campaign", "factory", "quick"];
export const SAFE_CODING_WORK_TYPES = ["auto", "patch", "slice", "quick"];

export function chatLayoutHtml() {
  return `
    <div class="chat-layout">
      <aside class="chat-library panel" data-testid="maker-chat-library"></aside>
      <aside class="chat-session-sidebar panel" data-testid="maker-chat-session-sidebar">
        <h4>Sessions</h4>
        <ul id="chat-session-list" class="chat-session-list"></ul>
        <button type="button" id="chat-new-session" class="linkish" data-testid="maker-chat-new-session">New session</button>
      </aside>
      <div class="chat-main">
        <section
          id="chat-compute-nodes"
          class="panel chat-compute-nodes muted"
          data-testid="maker-chat-compute-nodes"
          hidden
        >
          <h4>Compute</h4>
          <p class="chat-compute-nodes-caption">Session compute nodes</p>
          <ul id="chat-compute-nodes-list" class="chat-compute-nodes-list"></ul>
        </section>
        <section id="chat-operator-ribbons" class="chat-operator-ribbons hidden" data-testid="maker-chat-operator-ribbons">
          ${chatInterjectionRibbonHtml()}
          ${autopilotRibbonHtml({ compact: true })}
          ${enforcementRibbonHtml({ compact: true })}
        </section>
        <form id="chat-form" class="chat-form">
          <label>Project
            <select name="project_id" id="chat-project-select" data-testid="maker-chat-project-select" required></select>
          </label>
          <label>Work type
            <select name="work_type" id="chat-work-type" data-testid="maker-chat-work-type-select">
              ${(isSafeCodingUx() ? SAFE_CODING_WORK_TYPES : CHAT_WORK_TYPES)
                .map((wt) => `<option value="${wt}">${workTypeLabel(wt)}</option>`)
                .join("")}
            </select>
          </label>
          <label>Message
            <textarea name="message" id="chat-message" rows="4" required
              data-testid="maker-chat-message" placeholder="Describe the change, bug, or feature…"></textarea>
          </label>
          <fieldset class="chat-attachments">
            <legend>Attachments (optional)</legend>
            <label>File paths
              <textarea name="target_paths" id="chat-target-paths" rows="2"
                data-testid="maker-chat-target-path" placeholder="src/foo.py"></textarea>
            </label>
            <label>Failing test
              <input name="failing_test" id="chat-failing-test" type="text"
                data-testid="maker-chat-failing-test" placeholder="tests/test_foo.py::test_bar" />
            </label>
            <label>Stack trace
              <textarea name="stack_trace" id="chat-stack-trace" rows="3"
                data-testid="maker-chat-stack-trace" placeholder="AssertionError: …"></textarea>
            </label>
          </fieldset>
          <button type="submit" class="primary" data-testid="maker-chat-start">Send</button>
        </form>
        <aside id="chat-branch-panel" class="panel chat-branch-panel hidden" data-testid="maker-chat-branch-panel"></aside>
        <details id="chat-theater-mount" class="chat-theater-mount hidden" data-testid="maker-chat-theater-mount">
          <summary>
            Full run log (archive)
            <label class="chat-follow-live">
              <input type="checkbox" id="chat-theater-follow-live" data-testid="maker-chat-theater-follow-live" checked />
              Follow live
            </label>
            <a class="chat-theater-export linkish" href="#" download>Export transcript</a>
          </summary>
        </details>
        <ul id="chat-thread" class="chat-thread" data-testid="maker-chat-thread"></ul>
        <div id="chat-classifier-mount"></div>
      </div>
    </div>`;
}
