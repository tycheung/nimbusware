/** Capacity / compute / memory / LLM peel miss helpers for Maker web (`sak444-h` / `sak493-f` / `sak495-e` / `sak496-j` / `sak497-j` / `sak498-f`). */

import { mapHttp503PeelMiss, peelMissFromFetchError } from "../../../ui_shared/js/peel-http.js";

export { mapHttp503PeelMiss, peelMissFromFetchError };

function featureDomainMiss(body, domainCode, keywords) {
  if (!body || typeof body !== "object") return false;
  if (body.code === domainCode) return true;
  if (body.via === "broker_miss" || body.status === "degraded") return true;
  const feat = body.feature;
  if (typeof feat === "string") {
    const low = feat.toLowerCase();
    if (keywords.some((kw) => low.includes(kw))) {
      return body.via === "broker_miss" || (body.error != null && String(body.error).length > 0);
    }
  }
  return false;
}

export function isCapacityMiss(body) {
  if (!body || typeof body !== "object") return false;
  if (body.code === "broker_capacity_only") return true;
  if (body.capacity_source === "broker_miss" || body.fit_via === "broker_miss") return true;
  if (body.via === "broker_miss" || body.status === "degraded") return true;
  return false;
}

export function isDomainPeelMiss(body) {
  if (!body || typeof body !== "object") return false;
  return (
    body.via === "broker_miss" ||
    body.status === "degraded" ||
    body.code === "broker_compute_only" ||
    body.code === "broker_memory_only" ||
    body.code === "broker_sandbox_only" ||
    body.code === "broker_tools_only" ||
    body.code === "broker_research_only" ||
    body.code === "broker_egress_only" ||
    body.code === "broker_llm_unavailable" ||
    featureDomainMiss(body, "broker_memory_only", ["memory"]) ||
    featureDomainMiss(body, "broker_sandbox_only", ["sandbox"]) ||
    featureDomainMiss(body, "broker_tools_only", ["tools", "shell"]) ||
    featureDomainMiss(body, "broker_research_only", ["research"]) ||
    featureDomainMiss(body, "broker_egress_only", ["egress"]) ||
    featureDomainMiss(body, "broker_llm_unavailable", ["llm"])
  );
}

export function formatDomainMissMessage(body, fallback = "broker_miss") {
  if (!body || typeof body !== "object") return fallback;
  const err = body.error != null ? String(body.error) : "";
  if (err) return err;
  const feat = body.feature != null ? String(body.feature) : "";
  if (feat) return feat;
  const via = body.via != null ? String(body.via) : "";
  if (via) return via;
  return fallback;
}

/** Capacity-specific miss banner (`sak501-d`). */
export function formatCapacityMissMessage(body, fallback = "Capacity peel miss") {
  if (!body || typeof body !== "object") return fallback;
  const base = formatDomainMissMessage(body, fallback);
  const src = body.capacity_source != null ? String(body.capacity_source) : "";
  const fit = body.fit_via != null ? String(body.fit_via) : "";
  if (src || fit) {
    return `${base} (capacity_source=${src || "—"}, fit_via=${fit || "—"})`;
  }
  return base;
}

export function isBrokerMiss(body) {
  return isDomainPeelMiss(body) || isCapacityMiss(body); // sak498-f
}

export function missBannerText(body, fallback = "Broker capacity unavailable") {
  if (!isBrokerMiss(body)) return null;
  if (isCapacityMiss(body)) return formatCapacityMissMessage(body, fallback); // sak501-d
  if (isDomainPeelMiss(body)) return formatDomainMissMessage(body, fallback);
  const feature = body.feature ? ` (${body.feature})` : "";
  const err = body.error ? `: ${body.error}` : "";
  return `${fallback}${feature}${err}`;
}

export function toastIfMiss(body, toast, fallback) {
  const text = missBannerText(body, fallback);
  if (text) {
    toast(text, "error");
    return true;
  }
  return false;
}

/** Aggregate partial multi-fetch misses into one toast (`sak496-j`). */
export function toastIfMisses(misses, toast, fallback) {
  const bodies = (misses || []).filter((body) => isBrokerMiss(body));
  if (!bodies.length) return false;
  const features = [
    ...new Set(
      bodies
        .map((body) => (body.feature ? String(body.feature) : ""))
        .filter(Boolean),
    ),
  ];
  const detail =
    features.length > 1
      ? `${fallback} (${features.slice(0, 3).join(", ")}${features.length > 3 ? ", …" : ""})`
      : missBannerText(bodies[0], fallback) || fallback;
  toast(detail, "error");
  return true;
}
