/**
 * ORBIS Admin — Service Worker
 * Strategy:
 *   - /static/admin/* and /static/css/admin/* and /static/js/admin/* → cache-first
 *   - /admin/api/* → network-only (NO cache, real data)
 *   - /admin/* navigations → network-first, fallback to /admin/dashboard (offline)
 *   - All other requests → bypass
 *
 * Versioned cache name — bump when CSS/JS changes to bust.
 */
const CACHE_VERSION = 'orbis-admin-v1';
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const ASSET_CACHE = `${CACHE_VERSION}-assets`;

const SHELL_URLS = [
  '/admin/dashboard',
  '/static/css/admin/tokens.css',
  '/static/css/admin/base.css',
  '/static/css/admin/layout.css',
  '/static/css/admin/components.css',
  '/static/css/admin/motion.css',
  '/static/js/admin/theme.js',
  '/static/js/admin/shortcuts.js',
  '/static/js/admin/charts.js',
  '/static/manifest-admin.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(CACHE_VERSION)).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // API: network only, no cache
  if (url.pathname.startsWith('/admin/api/')) return;

  // Admin static assets: cache-first
  if (url.pathname.startsWith('/static/css/admin/') ||
      url.pathname.startsWith('/static/js/admin/') ||
      url.pathname.startsWith('/static/manifest-admin.json')) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(ASSET_CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => cached))
    );
    return;
  }

  // Admin navigations: network-first, fallback cached /admin/dashboard
  if (url.pathname.startsWith('/admin/') || url.pathname === '/admin') {
    event.respondWith(
      fetch(req).then((res) => {
        if (res.ok && req.mode === 'navigate') {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put('/admin/dashboard', copy));
        }
        return res;
      }).catch(() => caches.match('/admin/dashboard'))
    );
  }
});
