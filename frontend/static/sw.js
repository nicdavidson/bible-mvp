/**
 * BibleMVP Service Worker
 * Provides offline caching for the app shell and recently viewed content.
 */

const CACHE_NAME = 'biblemvp-v1';
const STATIC_CACHE = 'biblemvp-static-v1';
const CONTENT_CACHE = 'biblemvp-content-v1';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/icons/icon.svg',
    '/static/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name.startsWith('biblemvp-') &&
                                   name !== STATIC_CACHE &&
                                   name !== CONTENT_CACHE)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip cross-origin requests (like Alpine.js CDN)
    if (url.origin !== location.origin) return;

    // API requests - network first, cache fallback for passages
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstWithCache(event.request));
        return;
    }

    // Static assets - cache first
    event.respondWith(cacheFirst(event.request));
});

// Cache-first strategy for static assets
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        // Return offline fallback if available
        return caches.match('/');
    }
}

// Network-first strategy with cache fallback for API calls
async function networkFirstWithCache(request) {
    const url = new URL(request.url);

    try {
        const response = await fetch(request);

        // Cache successful passage/interlinear responses
        if (response.ok &&
            (url.pathname.startsWith('/api/passage/') ||
             url.pathname.startsWith('/api/interlinear/'))) {
            const cache = await caches.open(CONTENT_CACHE);
            cache.put(request, response.clone());

            // Limit content cache size
            limitCacheSize(CONTENT_CACHE, 100);
        }

        return response;
    } catch (error) {
        // Try to serve from cache when offline
        const cached = await caches.match(request);
        if (cached) return cached;

        // Return error response
        return new Response(JSON.stringify({
            error: 'offline',
            detail: 'You are offline and this content is not cached.'
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Limit cache size by removing oldest entries
async function limitCacheSize(cacheName, maxItems) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();

    if (keys.length > maxItems) {
        // Delete oldest entries (first in list)
        const deleteCount = keys.length - maxItems;
        for (let i = 0; i < deleteCount; i++) {
            await cache.delete(keys[i]);
        }
    }
}
