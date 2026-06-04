import { getBootstrap } from "./api-client.js";
import { loadRoute } from "./tab-loader.js";

function loadRouteOnInit() {
  loadRoute(parseRoute()).catch(console.error);
}

const TABS = [
  { id: "home", hash: "/home", label: "Home" },
  { id: "build", hash: "/build", label: "Build" },
  { id: "review", hash: "/review", label: "Review" },
  { id: "progress", hash: "/progress", label: "Progress" },
  { id: "models", hash: "/models", label: "Models" },
  { id: "settings", hash: "/settings", label: "Settings" },
];

function parseRoute() {
  const hash = window.location.hash.replace(/^#/, "") || "/home";
  const path = hash.split("?")[0] || "/home";
  return path.startsWith("/") ? path : `/${path}`;
}

function applyQueryToRunId() {
  const params = new URLSearchParams(window.location.search);
  const fromHash = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const runId = params.get("run_id") || fromHash.get("run_id");
  if (runId) {
    const el = document.getElementById("run-theater-run-id");
    if (el) el.value = runId;
  }
}

function makerShellFactory() {
  return {
    tabs: TABS,
    route: "/home",
    statusText: "",
    toastMsg: "",
    toastKind: "info",
    editionLabel: "",
    init() {
      this.route = parseRoute();
      applyQueryToRunId();
      const b = getBootstrap();
      this.editionLabel = `Edition: ${b.edition || "individual"}${b.quick_mode ? " (quick)" : ""}`;
      window.addEventListener("hashchange", () => {
        this.route = parseRoute();
        applyQueryToRunId();
        window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
      });
      loadRouteOnInit();
      window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
    },
    navigate(hash) {
      window.location.hash = hash;
      this.route = parseRoute();
      window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
    },
    showToast(detail) {
      this.toastMsg = detail?.message || "";
      this.toastKind = detail?.kind || "info";
      if (this.toastMsg) {
        setTimeout(() => {
          this.toastMsg = "";
        }, 5000);
      }
    },
  };
}

document.addEventListener("alpine:init", () => {
  window.Alpine.data("makerShell", makerShellFactory);
});
