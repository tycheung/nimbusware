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
    return Object.entries(raw)
      .filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
      .join(" · ");
  }
  return String(raw).trim();
}
