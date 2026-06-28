// Minimal service worker — PWA "installable" criteria pura karne ke liye.
// Heavy offline-caching nahi kar raha (Streamlit app live data pe chalta hai,
// isliye full offline support iska use-case nahi hai) — bas install-prompt
// trigger hone ke liye browser ko ek active service worker dikhana hai.

const CACHE_NAME = "market-dashboard-shell-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Pass-through fetch — koi custom caching nahi, sirf network se serve karo.
// (Live market data ke liye stale cache dikhana galat hoga.)
self.addEventListener("fetch", (event) => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return new Response("Offline — internet connection check karo.", {
        status: 503,
        headers: { "Content-Type": "text/plain" },
      });
    })
  );
});
