import { getBootstrap } from "./api-client.js";
import { loadRoute } from "./tab-loader.js";

function loadRouteOnInit() {
  loadRoute(parseRoute()).catch(console.error);
}

const ALL_TABS = [
  { id: "home", hash: "/home", label: "Home" },
  { id: "build", hash: "/build", label: "Build" },
  { id: "review", hash: "/review", label: "Review" },
  { id: "progress", hash: "/progress", label: "Progress" },
  { id: "models", hash: "/models", label: "Models" },
  { id: "settings", hash: "/settings", label: "Settings" },
];

const MOBILE_TABS = [
  { id: "progress", hash: "/progress", label: "Progress" },
  { id: "review", hash: "/review", label: "Review" },
];

const MOBILE_ROUTES = new Set(["/progress", "/review"]);

export function detectMobileMode() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("mobile") === "1") return true;
  return window.matchMedia("(max-width: 720px)").matches;
}

function parseRoute() {
  const hash = window.location.hash.replace(/^#/, "") || "/home";
  const path = hash.split("?")[0] || "/home";
  return path.startsWith("/") ? path : `/${path}`;
}

function setRunIdValue(value) {
  const canonical = document.getElementById("run-theater-run-id");
  if (canonical) canonical.value = value;
  for (const id of ["mobile-run-id", "desktop-run-id"]) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }
}

function applyQueryToRunId() {
  const params = new URLSearchParams(window.location.search);
  const fromHash = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const runId = params.get("run_id") || fromHash.get("run_id");
  if (runId) setRunIdValue(runId);
}

function wireRunIdSync() {
  const canonical = document.getElementById("run-theater-run-id");
  if (!canonical) return;
  const pushFromVisible = (el) => {
    if (!el) return;
    el.addEventListener("input", () => {
      canonical.value = el.value;
    });
    if (el.value && !canonical.value) canonical.value = el.value;
  };
  pushFromVisible(document.getElementById("mobile-run-id"));
  pushFromVisible(document.getElementById("desktop-run-id"));
}

function makerShellFactory() {
  return {
    tabs: ALL_TABS,
    mobileMode: false,
    route: "/home",
    statusText: "",
    toastMsg: "",
    toastKind: "info",
    editionLabel: "",
    quickModeActive: false,
    quickBannerDismissed: false,
    init() {
      this.mobileMode = detectMobileMode();
      if (this.mobileMode) {
        document.body.classList.add("mobile-mode");
        this.tabs = MOBILE_TABS;
        const route = parseRoute();
        if (!MOBILE_ROUTES.has(route)) {
          window.location.hash = "#/progress";
        }
      } else {
        this.tabs = ALL_TABS;
      }
      this.route = parseRoute();
      applyQueryToRunId();
      wireRunIdSync();
      const b = getBootstrap();
      this.quickModeActive = Boolean(b.quick_mode);
      this.quickBannerDismissed =
        sessionStorage.getItem("maker_quick_banner_dismissed") === "1";
      this.editionLabel = `Edition: ${b.edition || "individual"}${b.quick_mode ? " (quick)" : ""}`;
      window.addEventListener("hashchange", () => {
        this.route = parseRoute();
        applyQueryToRunId();
        window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
      });
      window.matchMedia("(max-width: 720px)").addEventListener("change", (ev) => {
        if (ev.matches !== this.mobileMode) window.location.reload();
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
    dismissQuickBanner() {
      this.quickBannerDismissed = true;
      sessionStorage.setItem("maker_quick_banner_dismissed", "1");
    },
  };
}

document.addEventListener("alpine:init", () => {
  window.Alpine.data("makerShell", makerShellFactory);
});
