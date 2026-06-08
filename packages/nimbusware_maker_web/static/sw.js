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

self.addEventListener("push", (event) => {
  const payload = event.data ? event.data.text() : "Campaign update";
  event.waitUntil(self.registration.showNotification("Nimbusware Maker", { body: payload, tag: "maker-run" }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("./#/progress"));
});
