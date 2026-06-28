const CI_STAGE_PREFIXES = ["ci.", "deploy.", "terraform."];

export interface DeployLinks {
  apiUrl: string;
  webUrl: string;
  ciStatus: string;
  ciDetail: string;
}

export function deployLinksFromTimeline(events: unknown[]): DeployLinks {
  let ciStatus = "not_started";
  let ciDetail = "No CI workflow events yet";
  let apiUrl = "";
  let webUrl = "";

  for (const raw of events || []) {
    const ev = raw as { metadata?: Record<string, unknown> };
    const meta = ev.metadata || {};
    if (!apiUrl && meta.api_url) apiUrl = String(meta.api_url);
    if (!webUrl && meta.web_url) webUrl = String(meta.web_url);
    const urls = meta.live_urls;
    if (urls && typeof urls === "object") {
      const live = urls as Record<string, string>;
      if (!apiUrl && live.api) apiUrl = String(live.api);
      if (!webUrl && live.web) webUrl = String(live.web);
    }
  }

  for (const raw of [...(events || [])].reverse()) {
    const ev = raw as { event_type?: string; payload?: Record<string, unknown>; metadata?: Record<string, unknown> };
    const stage = String(ev.payload?.stage_name || "");
    if (!stage) continue;
    const lower = stage.toLowerCase();
    if (!CI_STAGE_PREFIXES.some((p) => lower.startsWith(p))) continue;
    if (ev.event_type === "stage.passed") {
      ciStatus = "passed";
      ciDetail = String(ev.metadata?.detail || ev.payload?.detail || stage);
    } else if (ev.event_type === "stage.failed") {
      ciStatus = "failed";
      ciDetail = String(ev.metadata?.detail || ev.payload?.detail || stage);
    } else if (ev.event_type === "stage.started" && ciStatus === "not_started") {
      ciStatus = "running";
      ciDetail = stage;
    }
    if (ciStatus !== "not_started") break;
  }

  return { apiUrl, webUrl, ciStatus, ciDetail };
}
