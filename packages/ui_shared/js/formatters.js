export function fmtRate(value) {
  if (typeof value !== "number") return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function fmtFit(value) {
  if (typeof value !== "number") return "—";
  return value.toFixed(2);
}

export function formatGateSummary(raw) {
  if (raw == null) return "";
  if (typeof raw === "string") return raw.trim();
  if (typeof raw === "object") {
    const parts = [];
    for (const [k, v] of Object.entries(raw)) {
      if (v == null || v === "") continue;
      const label = k.replace(/^slice\./, "").replaceAll("_", " ");
      const verdict = typeof v === "object" ? v.verdict || v.status || JSON.stringify(v) : String(v);
      parts.push(`${label}: ${verdict}`);
    }
    return parts.join(" · ");
  }
  return String(raw).trim();
}
