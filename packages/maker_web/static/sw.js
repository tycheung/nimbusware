const CACHE = "maker-shell-v1";
const SHELL = ["./", "./styles.css", "./tokens.css", "./manifest.json", "./css/theater.css"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request).then((hit) => hit || caches.match("./"))),
  );
});

function parsePushPayload(event) {
  const raw = event.data ? event.data.text() : "";
  if (!raw) {
    return { title: "Nimbusware Maker", body: "Campaign update", run_id: "" };
  }
  try {
    const parsed = JSON.parse(raw);
    return {
      title: parsed.title || "Nimbusware Maker",
      body: parsed.body || raw,
      run_id: parsed.run_id || "",
    };
  } catch {
    return { title: "Nimbusware Maker", body: raw, run_id: "" };
  }
}

self.addEventListener("push", (event) => {
  const payload = parsePushPayload(event);
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      tag: payload.run_id ? `maker-run-${payload.run_id}` : "maker-run",
      data: { run_id: payload.run_id },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const runId = event.notification?.data?.run_id || "";
  const target = runId ? `./#/progress?run_id=${encodeURIComponent(runId)}` : "./#/progress";
  event.waitUntil(clients.openWindow(target));
});
