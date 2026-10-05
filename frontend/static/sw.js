/**
 * BibleMVP Service Worker: offline app shell + recently viewed API content.
 * Registered with scope '/' (server sends Service-Worker-Allowed: /).
 * Structured offline data (downloads, auto-cached chapters) lives in IndexedDB,
 * written by the app itself; this worker only caches HTTP responses.
 */

// __SW_VERSION__ is replaced at Docker build time with the git commit hash.
const SW_VERSION = '__SW_VERSION__';
const STATIC_CACHE = `biblemvp-static-${SW_VERSION}`;  // app shell: one per deploy
const CONTENT_CACHE = 'biblemvp-content';               // API data: survives deploys

// Exactly the URLs index.html requests (versioned ones carry ?v=)
const V = `?v=${SW_VERSION}`;
const SHELL = [
    '/', '/config.js', '/static/manifest.json', '/static/icons/icon.svg',
    '/static/vendor/alpine-3.17.4.min.js', '/static/vendor/supabase-2.117.2.min.js',
    ...[
        '/static/css/style.css', '/static/js/app.js', '/static/js/offline-storage.js',
        '/static/js/supabase-client.js',
        ...['tts', 'menus', 'share', 'feedback', 'tags', 'selection', 'offline', 'plans', 'study_extras']
            .map(m => `/static/js/modules/${m}.js`),
    ].map(u => u + V),
];

const CACHEABLE_API = [
    /^\/api\/passage\//, /^\/api\/verse\//, /^\/api\/word\//, /^\/api\/word-alignment/,
    /^\/api\/topics\//, /^\/api\/reading-plans/, /^\/api\/devotional/,
];
const CONTENT_MAX = 300;

self.addEventListener('install', event => {
    // cache:'reload' so we never precache a stale copy from the HTTP cache
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(SHELL.map(u => new Request(u, { cache: 'reload' }))))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(names => Promise.all(names
                .filter(n => n.startsWith('biblemvp') && n !== STATIC_CACHE && n !== CONTENT_CACHE)
                .map(n => caches.delete(n))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const req = event.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    if (url.origin !== location.origin) return;

    if (req.mode === 'navigate') {
        // Every app route serves the same index.html: network first, cached shell offline
        event.respondWith(fetch(req).catch(() => caches.match('/', { cacheName: STATIC_CACHE })));
    } else if (url.pathname.startsWith('/api/')) {
        if (CACHEABLE_API.some(p => p.test(url.pathname))) event.respondWith(networkFirst(event, req));
        // other API calls: not intercepted
    } else if (url.pathname.startsWith('/static/') || url.pathname === '/config.js') {
        event.respondWith(cacheFirst(req));
    }
});

// Static files: versioned URLs are immutable, and the shell cache is per deploy.
async function cacheFirst(req) {
    const cached = await caches.match(req);
    if (cached) return cached;
    const res = await fetch(req);
    if (res.ok) {
        const copy = res.clone();  // clone now: the page may consume the body first
        caches.open(STATIC_CACHE).then(c => c.put(req, copy)).catch(() => {});
    }
    return res;
}

async function networkFirst(event, req) {
    let res;
    try {
        res = await fetch(req);
    } catch (err) {
        const cached = await caches.match(req, { cacheName: CONTENT_CACHE });
        return cached || new Response(
            JSON.stringify({ error: 'offline', detail: 'You are offline and this content is not cached.', offline: true }),
            { status: 503, headers: { 'Content-Type': 'application/json' } });
    }
    // Cache failures (quota, private mode) must never turn a good response into an error
    if (res.ok) {
        const copy = res.clone();
        event.waitUntil(caches.open(CONTENT_CACHE)
            .then(c => c.put(req, copy).then(() => trim(c)))
            .catch(() => {}));
    }
    return res;
}

// ponytail: FIFO by insertion order; LRU only if 300 entries proves too few
async function trim(cache) {
    const keys = await cache.keys();
    for (const k of keys.slice(0, Math.max(0, keys.length - CONTENT_MAX))) await cache.delete(k);
}
