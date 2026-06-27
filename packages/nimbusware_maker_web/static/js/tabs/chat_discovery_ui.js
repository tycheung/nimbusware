import { apiJson, toast } from "../api-client.js";
import { readSoloDiscipline } from "./settings_solo_discipline_ui.js";

const ANSWER_CHIPS = {
  client_form: ["Web app", "Mobile (web-first)", "Both", "You pick"],
  backend_stack: ["Python/FastAPI", "Node", "No preference"],
  frontend_stack: ["React", "Vue", "No preference"],
  hosting: ["Local only", "Cloud later", "Decide later"],
};

export function getScopeDiscoveryState(root) {
  return root._scopeDiscoveryState || null;
}

export function clearScopeDiscoveryState(root) {
  delete root._scopeDiscoveryState;
  root._scopeDiscoveryRequired = false;
  root.querySelector("#chat-discovery-mount")?.replaceChildren();
}

function needsFullstackDiscovery(classification, message) {
  const profile = String(classification?.suggested_profile || "");
  const wt = String(classification?.work_type || "");
  if (profile === "campaign_micro_slice") return false;
  if (profile === "campaign_fullstack" || wt === "campaign") return true;
  return false;
}

function manifestSummary(manifest) {
  if (!manifest || typeof manifest !== "object") return "";
  const surfaces = Array.isArray(manifest.surfaces) ? manifest.surfaces.join(", ") : "";
  const stacks = manifest.stacks && typeof manifest.stacks === "object"
    ? Object.entries(manifest.stacks).map(([k, v]) => `${k}: ${v}`).join("; ")
    : "";
  return [surfaces ? `Surfaces: ${surfaces}` : "", stacks ? `Stacks: ${stacks}` : ""]
    .filter(Boolean)
    .join(" · ");
}

export function plainManifestApprovalText(manifest, state) {
  if (!manifest || typeof manifest !== "object") return "";
  const surfaces = Array.isArray(manifest.surfaces) ? manifest.surfaces : [];
  const stacks = manifest.stacks && typeof manifest.stacks === "object" ? manifest.stacks : {};
  const productParts = [];
  if (surfaces.includes("web")) productParts.push("web UI");
  if (surfaces.includes("api")) productParts.push("REST API");
  if (surfaces.includes("contract")) productParts.push("shared contracts");
  const stackParts = [];
  if (stacks.web) stackParts.push(`${stacks.web} frontend`);
  if (stacks.api) stackParts.push(`${stacks.api} backend`);
  const product = productParts.length ? productParts.join(" + ") : "full-stack app";
  const stackLine = stackParts.length ? ` (${stackParts.join(", ")})` : "";
  const lead = state?.recommend_for_me ? "Recommended plan" : "You are approving";
  return `${lead}: ${product}${stackLine} with automated tests`;
}

async function confirmScopeState(state) {
  const body = await apiJson("/chat/scope/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
  return body.scope;
}

function renderManifestPreview(mount, state, { onConfirmed } = {}) {
  const manifest = state?.stack_manifest;
  if (!manifest) return;
  const card = document.createElement("article");
  card.className = "panel chat-scope-manifest-card";
  card.dataset.testid = "maker-chat-scope-manifest";
  const title = document.createElement("h4");
  title.textContent = state.recommend_for_me ? "Recommended stack manifest" : "Scope manifest";
  card.appendChild(title);
  const plain = document.createElement("p");
  plain.className = "chat-manifest-plain";
  plain.dataset.testid = "maker-chat-scope-manifest-plain";
  plain.textContent = plainManifestApprovalText(manifest, state);
  card.appendChild(plain);
  const summary = document.createElement("p");
  summary.className = "muted";
  summary.textContent = manifestSummary(manifest);
  card.appendChild(summary);
  if (!state.scope_confirmed) {
    const actions = document.createElement("div");
    actions.className = "actions";
    const approve = document.createElement("button");
    approve.type = "button";
    approve.className = "primary";
    approve.textContent = "Approve manifest";
    approve.title = "Freeze the stack manifest and unlock run start";
    approve.dataset.testid = "maker-chat-scope-confirm";
    approve.addEventListener("click", async () => {
      approve.disabled = true;
      try {
        const confirmed = await confirmScopeState(state);
        onConfirmed?.(confirmed);
        toast("Manifest approved — you can start the run", "success");
        mount.replaceChildren();
        renderManifestPreview(mount, confirmed, { onConfirmed });
      } catch (e) {
        toast(String(e.message || e), "error");
        approve.disabled = false;
      }
    });
    actions.appendChild(approve);
    card.appendChild(actions);
  } else {
    const ok = document.createElement("p");
    ok.className = "muted";
    ok.dataset.testid = "maker-chat-scope-confirmed";
    ok.textContent = "Manifest approved";
    card.appendChild(ok);
  }
  mount.appendChild(card);
}

async function gatherScope(state, answers, { recommendForMe = false } = {}) {
  const body = await apiJson("/chat/scope/gather", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      state,
      answers,
      recommend_for_me: recommendForMe,
    }),
  });
  return body.scope;
}

export async function mountScopeDiscoveryIfNeeded(root, classification, message) {
  clearScopeDiscoveryState(root);
  if (!needsFullstackDiscovery(classification, message)) {
    return true;
  }
  root._scopeDiscoveryRequired = true;
  const mount = root.querySelector("#chat-discovery-mount");
  if (!mount) return true;

  let state;
  try {
    const resp = await apiJson("/chat/scope/discover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_prompt: message }),
    });
    state = resp.scope;
  } catch (e) {
    toast(String(e.message || e), "error");
    return false;
  }

  if (state.discovery_complete) {
    root._scopeDiscoveryState = state;
    renderManifestPreview(mount, state, {
      onConfirmed: (confirmed) => {
        root._scopeDiscoveryState = confirmed;
      },
    });
    return true;
  }

  mount.replaceChildren();
  const card = document.createElement("article");
  card.className = "panel chat-discovery-card";
  card.dataset.testid = "maker-chat-discovery-card";
  const headline = document.createElement("h4");
  headline.textContent = "Scope discovery — answer a few questions before starting";
  card.appendChild(headline);

  const answers = [];
  let currentState = state;

  const recommendBtn = document.createElement("button");
  recommendBtn.type = "button";
  recommendBtn.className = "primary";
  recommendBtn.textContent = "Recommend for me";
  recommendBtn.title = "Let Nimbusware infer surfaces and stacks from your answers";
  recommendBtn.dataset.testid = "maker-chat-recommend-for-me";
  recommendBtn.addEventListener("click", async () => {
    recommendBtn.disabled = true;
    try {
      currentState = await gatherScope(currentState, answers, { recommendForMe: true });
      root._scopeDiscoveryState = currentState;
      mount.replaceChildren();
      renderManifestPreview(mount, currentState, {
        onConfirmed: (confirmed) => {
          root._scopeDiscoveryState = confirmed;
        },
      });
      toast("Stack manifest ready — you can start the run", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
      recommendBtn.disabled = false;
    }
  });
  card.appendChild(recommendBtn);

  for (const q of state.questions_emitted || []) {
    const block = document.createElement("div");
    block.className = "chat-discovery-question";
    const label = document.createElement("p");
    label.textContent = q.question;
    block.appendChild(label);
    const chips = document.createElement("div");
    chips.className = "actions chat-action-chips";
    for (const chipLabel of ANSWER_CHIPS[q.id] || ["Answer…"]) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.textContent = chipLabel;
      chip.dataset.testid = `maker-chat-discovery-${q.id}-${chipLabel.replace(/\W+/g, "-").toLowerCase()}`;
      chip.addEventListener("click", async () => {
        for (const c of chips.querySelectorAll("button")) c.disabled = true;
        answers.push({ question_id: q.id, question: q.question, answer: chipLabel });
        try {
          currentState = await gatherScope(currentState, answers);
          if (currentState.discovery_complete) {
            root._scopeDiscoveryState = currentState;
            mount.replaceChildren();
            renderManifestPreview(mount, currentState, {
              onConfirmed: (confirmed) => {
                root._scopeDiscoveryState = confirmed;
              },
            });
            toast("Scope complete — you can start the run", "success");
          }
        } catch (e) {
          toast(String(e.message || e), "error");
          for (const c of chips.querySelectorAll("button")) c.disabled = false;
        }
      });
      chips.appendChild(chip);
    }
    block.appendChild(chips);
    card.appendChild(block);
  }

  mount.appendChild(card);
  return false;
}

export function scopeRequirementsPayload(root, message) {
  const base = { business_prompt: message };
  if (!root._scopeDiscoveryRequired) {
    return base;
  }
  const scopeState = getScopeDiscoveryState(root);
  if (!scopeState?.discovery_complete) {
    return base;
  }
  base.scope_discovery = scopeState;
  if (scopeState.stack_manifest) base.stack_manifest = scopeState.stack_manifest;
  if (scopeState.recommend_for_me) base.recommend_for_me = true;
  const hat = readSoloDiscipline();
  if (hat) base.solo_discipline = hat;
  return base;
}

export function discoveryBlocksStart(root, workType) {
  if (!root._scopeDiscoveryRequired) return false;
  const scopeState = getScopeDiscoveryState(root);
  return !scopeState?.discovery_complete;
}
