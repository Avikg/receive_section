const CACHE_NAME = 'wbsedcl-cache-v1';
const URLS_TO_CACHE = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/favicon.ico',
  '/static/offline.html'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(URLS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        // Optionally cache new requests
        caches.open(CACHE_NAME).then((cache) => {
          try {
            cache.put(event.request, networkResponse.clone());
          } catch (e) {
            // Some responses (opaque) might fail to be cached; ignore
          }
        });
        return networkResponse;
      }).catch(() => {
        // If navigation request, show offline fallback
        if (event.request.mode === 'navigate' || (event.request.headers.get('accept') || '').includes('text/html')) {
          return caches.match('/static/offline.html');
        }
      });
    })
  );
});
