import { mountHome } from "./tabs/home.js";
import { mountBuild } from "./tabs/build.js";
import { mountPlan } from "./tabs/plan.js";
import { mountReview } from "./tabs/review.js";
import { mountProgress, unmountProgress } from "./tabs/progress.js";
import { mountModels } from "./tabs/models.js";
import { mountSettings } from "./tabs/settings.js";
import { mountWizard } from "./tabs/wizard.js";
import { apiJson } from "./api-client.js";

const MOUNTERS = {
  "/home": { el: "home-mount", fn: mountHome },
  "/build": { el: "build-mount", fn: mountBuild },
  "/plan": { el: "plan-mount", fn: mountPlan },
  "/review": { el: "review-mount", fn: mountReview },
  "/progress": { el: "progress-mount", fn: mountProgress },
  "/models": { el: "models-mount", fn: mountModels },
  "/settings": { el: "settings-mount", fn: mountSettings },
};

let lastRoute = "";

export async function loadRoute(route) {
  if (lastRoute === "/progress" && route !== "/progress") {
    unmountProgress();
  }
  lastRoute = route;

  if (route === "/home") {
    try {
      const ob = await apiJson("/platform/onboarding");
      if (!ob.onboarded) {
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

window.addEventListener("maker-route", (ev) => {
  loadRoute(ev.detail?.route || "/home").catch(console.error);
});
