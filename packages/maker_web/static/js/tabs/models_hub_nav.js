export const MODEL_PRESETS = [
  { id: "quality", label: "Quality", hint: "Larger context, slower" },
  { id: "balanced", label: "Balanced", hint: "Default trade-off" },
  { id: "speed", label: "Speed", hint: "Smaller context, faster" },
];

export function gpuGroupLabel(group, index) {
  if (!Array.isArray(group) || !group.length) return `Pool ${index}`;
  return `Pool ${index}: ${group.join(", ")}`;
}

export function formatBytes(n) {
  if (n == null || Number.isNaN(Number(n))) return "";
  const gb = Number(n) / 1e9;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${(Number(n) / 1e6).toFixed(0)} MB`;
}

export function maskSecret(set) {
  return set ? "••••••••••" : "";
}

export function hubSectionFromUrl() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const section = params.get("section");
  if (section === "api-connections") return "api-connections";
  return "local";
}

export function setHubSection(section) {
  const base = window.location.hash.split("?")[0] || "#/models";
  const params = new URLSearchParams();
  if (section === "api-connections") params.set("section", "api-connections");
  const qs = params.toString();
  window.location.hash = qs ? `${base}?${qs}` : base;
}

export function scrollHubSection(root, section) {
  const el = root.querySelector(section === "api-connections" ? "#api-connections" : "#local");
  el?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function wireHubNav(root) {
  function activateNav(section) {
    root.querySelectorAll(".model-hub-nav-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.section === section);
    });
    scrollHubSection(root, section);
  }

  root.querySelectorAll(".model-hub-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section || "local";
      setHubSection(section);
      activateNav(section);
    });
  });
  activateNav(hubSectionFromUrl());
}
