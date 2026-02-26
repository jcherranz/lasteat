var CACHE_NAME = 'lasteat-v7';
var STATIC_ASSETS = [
  '/',
  '/app.js',
  '/data.js',
  '/manifest.json',
  '/og.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/fonts/cormorant-garamond-300-latin.woff2',
  '/fonts/cormorant-garamond-600-latin.woff2',
  '/fonts/dm-sans-300-latin.woff2',
  '/fonts/dm-sans-400-latin.woff2',
  '/fonts/dm-sans-500-latin.woff2'
];

/* Install: cache static assets */
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

/* Activate: clean old caches */
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME; })
          .map(function(n) { return caches.delete(n); })
      );
    })
  );
  self.clients.claim();
});

/* Fetch: network-first for HTML, cache-first for assets */
self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  /* Skip non-GET and cross-origin */
  if (event.request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  /* HTML pages: network-first (so updates are seen quickly) */
  if (event.request.mode === 'navigate' || url.pathname.endsWith('.html')) {
    event.respondWith(
      fetch(event.request).then(function(response) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, clone);
        });
        return response;
      }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  /* data.js: network-first (so restaurant data stays fresh) */
  if (url.pathname === '/data.js') {
    event.respondWith(
      fetch(event.request).then(function(response) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, clone);
        });
        return response;
      }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  /* Other assets: cache-first */
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      if (cached) return cached;
      return fetch(event.request).then(function(response) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, clone);
        });
        return response;
      });
    })
  );
});
