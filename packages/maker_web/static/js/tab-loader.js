import { mountChat, unmountChat } from "./tabs/chat.js";
import { mountChatJoin } from "./tabs/chat_join.js";
import { mountHome } from "./tabs/home.js";
import { mountBuild } from "./tabs/build.js";
import { mountPlan, unmountPlan } from "./tabs/plan.js";
import { mountReview } from "./tabs/review.js";
import { mountProgress, unmountProgress } from "./tabs/progress.js";
import { mountModels } from "./tabs/models.js";
import { mountSettings } from "./tabs/settings.js";
import { mountWizard } from "./tabs/wizard.js";
import { apiJson, toast } from "./api-client.js";
import { isDomainPeelMiss, toastIfMiss } from "./broker_miss.js"; // sak499-b

import { mountManagerScope } from "./tabs/manager_scope_ui.js";

const MOUNTERS = {
  "/chat": { el: "chat-mount", fn: mountChat },
  "/chat/join": { el: "chat-join-mount", fn: mountChatJoin },
  "/home": { el: "home-mount", fn: mountHome },
  "/build": { el: "build-mount", fn: mountBuild },
  "/plan": { el: "plan-mount", fn: mountPlan },
  "/review": { el: "review-mount", fn: mountReview },
  "/progress": { el: "progress-mount", fn: mountProgress },
  "/scope": { el: "scope-mount", fn: mountManagerScope },
  "/models": { el: "models-mount", fn: mountModels },
  "/settings": { el: "settings-mount", fn: mountSettings },
};

let lastRoute = "";
let lastRouteKey = "";
let loadChain = Promise.resolve();

/** Path + hash query for tabs that bind run/session from the URL. */
function routeKey(route) {
  const hash = window.location.hash.replace(/^#/, "") || route;
  const qIdx = hash.indexOf("?");
  const q = qIdx >= 0 ? hash.slice(qIdx) : "";
  if (
    q &&
    (route === "/chat" || route === "/progress" || route === "/plan" || route === "/review")
  ) {
    return `${route}${q}`;
  }
  return route;
}

export function handleRouteLoadError(e) {
  if (String(e?.message || e) === "broker_miss") return;
  toast(String(e?.message || e), "error");
}

async function loadRouteInner(route) {
  // Same path+query is a no-op (avoids init double-mount wipe). Query changes
  // (e.g. #/chat → #/chat?run_id=…) must remount so theater/escalation bind.
  const key = routeKey(route);
  if (key === lastRouteKey) return;

  const prev = lastRoute;
  // Unmount whenever leaving or remounting these tabs (query-key change).
  if (prev === "/progress") unmountProgress();
  if (prev === "/plan") unmountPlan();
  if (prev === "/chat") unmountChat();
  lastRoute = route;
  lastRouteKey = key;

  if (route === "/home") {
    try {
      const ob = await apiJson("/platform/onboarding").catch((e) => ({
        via: "broker_miss",
        error: String(e.message || e),
        feature: "onboarding",
      }));
      if (isDomainPeelMiss(ob)) {
        toastIfMiss(ob, toast, "Onboarding unavailable");
      } else if (!ob.onboarded) {
        const w = document.getElementById("home-mount");
        if (w) await mountWizard(w);
        return;
      }
    } catch {
      /* continue */
    }
  }

  const spec = MOUNTERS[route];
  if (!spec) return;
  const root = document.getElementById(spec.el);
  if (!root) return;
  await spec.fn(root);
}

export function loadRoute(route) {
  const run = loadChain.then(() => loadRouteInner(route));
  loadChain = run.catch(() => {});
  return run;
}

window.addEventListener("maker-route", (ev) => {
  loadRoute(ev.detail?.route || "/chat").catch(handleRouteLoadError);
});
