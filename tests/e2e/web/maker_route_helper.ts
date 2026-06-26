import { Page } from "@playwright/test";

export async function activateMakerRoute(page: Page, route: string): Promise<void> {
  await page.evaluate((targetRoute) => {
    if (!localStorage.getItem("maker_archetype_subchoice")) {
      localStorage.setItem("maker_archetype_subchoice", "engineer");
    }
    document.querySelector("[data-testid='maker-archetype-picker']")?.remove();
    const current = window.location.hash;
    const qIdx = current.indexOf("?");
    const query = qIdx >= 0 ? current.slice(qIdx) : "";
    const normalized = targetRoute.startsWith("/") ? targetRoute : `/${targetRoute}`;
    const shell = document.querySelector("[x-data]") as HTMLElement & {
      _x_dataStack?: Array<{ route: string; navigate?: (hash: string) => void }>;
    };
    const data = shell?._x_dataStack?.[0];
    if (data?.navigate && !query) {
      data.navigate(normalized);
      return;
    }
    window.location.hash = `#${normalized}${query}`;
    if (data) {
      data.route = normalized;
    }
    window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: normalized } }));
  }, route);
}

/** Activate a full hash (e.g. ``#/chat?run_id=…``) without dynamic module imports. */
export async function activateMakerRouteHash(page: Page, hash: string): Promise<void> {
  await page.evaluate((targetHash) => {
    if (!localStorage.getItem("maker_archetype_subchoice")) {
      localStorage.setItem("maker_archetype_subchoice", "engineer");
    }
    document.querySelector("[data-testid='maker-archetype-picker']")?.remove();
    const h = targetHash.startsWith("#") ? targetHash : `#${targetHash}`;
    const path = h.replace(/^#/, "").split("?")[0] || "/chat";
    const normalized = path.startsWith("/") ? path : `/${path}`;
    window.location.hash = h;
    const shell = document.querySelector("[x-data]") as HTMLElement & {
      _x_dataStack?: Array<{ route: string }>;
    };
    const data = shell?._x_dataStack?.[0];
    if (data) {
      data.route = normalized;
    }
    window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: normalized } }));
  }, hash);
}
