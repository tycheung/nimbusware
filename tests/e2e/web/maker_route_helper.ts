import { Page } from "@playwright/test";

export async function activateMakerRoute(page: Page, route: string): Promise<void> {
  await page.evaluate(async (targetRoute) => {
    const current = window.location.hash;
    const qIdx = current.indexOf("?");
    const query = qIdx >= 0 ? current.slice(qIdx) : "";
    window.location.hash = `#${targetRoute}${query}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    const shell = document.querySelector("[x-data]") as HTMLElement & {
      _x_dataStack?: Array<{ route: string }>;
    };
    const data = shell?._x_dataStack?.[0];
    if (data) {
      data.route = targetRoute;
    }
    const { loadRoute } = await import("/v1/maker/app/js/tab-loader.js");
    await loadRoute(targetRoute);
  }, route);
}
