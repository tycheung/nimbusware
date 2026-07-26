import { Page } from "@playwright/test";

function normalizeRoute(route: string): string {
  const path = route.startsWith("/") ? route : `/${route}`;
  return path.split("?")[0] || "/chat";
}

/** Dismiss archetype picker and sync Alpine route without remounting when already there. */
export async function activateMakerRoute(page: Page, route: string): Promise<void> {
  const normalized = normalizeRoute(route);
  await page.evaluate((targetRoute) => {
    if (!localStorage.getItem("maker_archetype_subchoice")) {
      localStorage.setItem("maker_archetype_subchoice", "engineer");
    }
    document.querySelector("[data-testid='maker-archetype-picker']")?.remove();
    const shell = document.querySelector("[x-data]") as HTMLElement & {
      _x_dataStack?: Array<{ route: string; navigate?: (hash: string) => void }>;
    };
    const data = shell?._x_dataStack?.[0];
    const curHash = window.location.hash.replace(/^#/, "") || "/chat";
    const curPath = (curHash.split("?")[0] || "/chat").startsWith("/")
      ? curHash.split("?")[0] || "/chat"
      : `/${curHash.split("?")[0] || "chat"}`;

    if (data) data.route = targetRoute;

    // Already on this tab — do not remount (wipes in-flight UI / listeners).
    if (curPath === targetRoute) return;

    if (data?.navigate) {
      data.navigate(targetRoute);
      return;
    }
    window.location.hash = `#${targetRoute}`;
  }, normalized);

  await page.waitForFunction(
    (targetRoute) => {
      const shell = document.querySelector("[x-data]") as HTMLElement & {
        _x_dataStack?: Array<{ route: string }>;
      };
      return shell?._x_dataStack?.[0]?.route === targetRoute;
    },
    normalized,
    { timeout: 10_000 },
  );
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
    const shell = document.querySelector("[x-data]") as HTMLElement & {
      _x_dataStack?: Array<{ route: string; navigate?: (hash: string) => void }>;
    };
    const data = shell?._x_dataStack?.[0];
    if (data) data.route = normalized;

    if (window.location.hash === h) return;

    if (data?.navigate) {
      // navigate preserves query only for same path; pass full path+query when present
      const raw = h.replace(/^#/, "");
      data.navigate(raw.startsWith("/") ? raw : `/${raw}`);
      return;
    }
    window.location.hash = h;
  }, hash);

  await page.waitForFunction(
    (targetHash) => {
      const h = targetHash.startsWith("#") ? targetHash : `#${targetHash}`;
      const path = h.replace(/^#/, "").split("?")[0] || "/chat";
      const normalized = path.startsWith("/") ? path : `/${path}`;
      const shell = document.querySelector("[x-data]") as HTMLElement & {
        _x_dataStack?: Array<{ route: string }>;
      };
      return shell?._x_dataStack?.[0]?.route === normalized;
    },
    hash,
    { timeout: 10_000 },
  );
}
