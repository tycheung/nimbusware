export function fmtRate(v: unknown): string {
  if (typeof v !== "number") return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function fmtFit(v: unknown): string {
  if (typeof v !== "number") return "—";
  return v.toFixed(2);
}
