import { test, expect } from "@playwright/test";

test("mobile theater css enables scrollable compaction layout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v1/maker/app/");
  await page.evaluate(() => document.body.classList.add("mobile-mode"));
  const theaterCss = await page.evaluate(async () => {
    const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
    const href = links.find((link) => (link as HTMLLinkElement).href.includes("theater.css"));
    if (!href) return "";
    const resp = await fetch((href as HTMLLinkElement).href);
    return resp.text();
  });
  expect(theaterCss).toContain("body.mobile-mode #theater-list");
  expect(theaterCss).toMatch(/overflow-y:\s*(auto|scroll)/);
});

test("mobile shell keeps findings workspace selectors in styles", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v1/maker/app/");
  await page.evaluate(() => document.body.classList.add("mobile-mode"));
  const styles = await page.evaluate(async () => {
    const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
    const hrefs = await Promise.all(
      links.map(async (link) => {
        const url = (link as HTMLLinkElement).href;
        if (!url.includes(".css")) return "";
        const resp = await fetch(url);
        return resp.text();
      }),
    );
    return hrefs.join("\n");
  });
  expect(styles).toContain(".findings-workspace");
  expect(styles).toContain(".completion-cockpit");
});
