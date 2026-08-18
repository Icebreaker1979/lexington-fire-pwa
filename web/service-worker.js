const CACHE_NAME = "lexington-fire-v5";

const APP_SHELL = [
  "/",
  "/app",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
  );

  self.skipWaiting();
});


self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );

  self.clients.claim();
});


self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    return;
  }

  // Incident data must always come from the network.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
    );

    return;
  }

  // For the application itself, prefer the network
  // but fall back to the cached app shell.
  if (url.origin === self.location.origin) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();

          caches.open(CACHE_NAME)
            .then(cache => cache.put(request, copy));

          return response;
        })
        .catch(() =>
          caches.match(request)
            .then(response =>
              response || caches.match("/")
            )
        )
    );
  }
});
self.addEventListener("push", event => {
  let data = {
    title: "Lexington Fire",
    body: "New incident",
    url: "/"
  };

  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(
      data.title || "Lexington Fire",
      {
        body: data.body || "",
        icon: "/icons/icon-192.png",
        badge: "/icons/badge-96.png",
        data: {
          url: data.url || "/"
        },
        tag: data.incident_id
          ? `incident-${data.incident_id}`
          : undefined
      }
    )
  );
});


self.addEventListener("notificationclick", event => {
  event.notification.close();

  const url =
    event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({
      type: "window",
      includeUncontrolled: true
    }).then(windowClients => {
      for (const client of windowClients) {
        if ("focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }

      return clients.openWindow(url);
    })
  );
});
