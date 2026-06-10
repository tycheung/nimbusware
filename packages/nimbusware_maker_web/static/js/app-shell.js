import { apiJson, getBootstrap } from "./api-client.js";
import {
  getActiveProjectId,
  hydrateActiveRun,
  persistRunIdFromUrl,
  setActiveRun,
  syncRunIdToShell,
} from "./session-hub.js";
import { loadRoute } from "./tab-loader.js";

function loadRouteOnInit() {
  loadRoute(parseRoute()).catch(console.error);
}

const ALL_TABS = [
  { id: "chat", hash: "/chat", label: "Chat" },
  { id: "home", hash: "/home", label: "Home" },
  { id: "build", hash: "/build", label: "Build" },
  { id: "plan", hash: "/plan", label: "Plan" },
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
  const hash = window.location.hash.replace(/^#/, "") || "/chat";
  const path = hash.split("?")[0] || "/chat";
  return path.startsWith("/") ? path : `/${path}`;
}

function setRunIdValue(value) {
  syncRunIdToShell(value);
  const projectId = getActiveProjectId();
  if (projectId && value) setActiveRun(projectId, value);
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

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

async function maybeRegisterPushSubscription() {
  const push = getBootstrap().push;
  if (!push?.enabled || !push?.vapid_public_key) return;
  if (!detectMobileMode() || !("serviceWorker" in navigator) || !("PushManager" in window)) return;
  const permission =
    Notification.permission === "default"
      ? await Notification.requestPermission()
      : Notification.permission;
  if (permission !== "granted") return;
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(push.vapid_public_key),
    });
    const runId =
      document.getElementById("run-theater-run-id")?.value?.trim() ||
      new URLSearchParams(window.location.search).get("run_id") ||
      "";
    const payload = subscription.toJSON();
    if (runId) payload.run_id = runId;
    await apiJson("/maker/push-subscriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    /* optional — VAPID or browser may block */
  }
}

function maybeEnableMobilePush() {
  if (!detectMobileMode() || !("Notification" in window)) return;
  if (Notification.permission !== "default") return;
  Notification.requestPermission().catch(() => {});
}

function makerShellFactory() {
  return {
    tabs: ALL_TABS,
    mobileMode: false,
    route: "/chat",
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
      persistRunIdFromUrl();
      wireRunIdSync();
      hydrateActiveRun(apiJson).catch(() => {});
      const b = getBootstrap();
      this.quickModeActive = Boolean(b.quick_mode);
      this.quickBannerDismissed =
        sessionStorage.getItem("maker_quick_banner_dismissed") === "1";
      this.editionLabel = `Edition: ${b.edition || "individual"}${b.quick_mode ? " (quick)" : ""}`;
      window.addEventListener("hashchange", () => {
        this.route = parseRoute();
        applyQueryToRunId();
        persistRunIdFromUrl();
        window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
      });
      window.matchMedia("(max-width: 720px)").addEventListener("change", (ev) => {
        if (ev.matches !== this.mobileMode) window.location.reload();
      });
      loadRouteOnInit();
      window.dispatchEvent(new CustomEvent("maker-route", { detail: { route: this.route } }));
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("./sw.js").catch(() => {});
      }
      maybeEnableMobilePush();
      maybeRegisterPushSubscription();
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
