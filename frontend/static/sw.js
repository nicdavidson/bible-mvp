/**
 * BibleMVP Service Worker
 * Provides offline caching for the app shell and recently viewed content.
 * Integrates with IndexedDB via postMessage for smart offline storage.
 */

const CACHE_NAME = 'biblemvp-v7';
const STATIC_CACHE = 'biblemvp-static-v7';
const CONTENT_CACHE = 'biblemvp-content-v7';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/offline-storage.js',
    '/static/js/supabase-client.js',
    '/static/icons/icon.svg',
    '/static/manifest.json'
];

// API endpoints that should be cached for offline use
const CACHEABLE_API_PATTERNS = [
    /^\/api\/passage\//,
    /^\/api\/interlinear\//,
    /^\/api\/verse\//,
    /^\/api\/word\//,
    /^\/api\/word-alignment/,
    /^\/api\/offline\//
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[SW] Installing service worker v7...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => {
                console.log('[SW] Static assets cached, calling skipWaiting');
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating service worker v7...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name.startsWith('biblemvp-') &&
                                   name !== STATIC_CACHE &&
                                   name !== CONTENT_CACHE)
                    .map(name => caches.delete(name))
            );
        }).then(() => {
            console.log('[SW] Claiming clients');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip cross-origin requests (like Alpine.js CDN)
    if (url.origin !== location.origin) return;

    // API requests - network first with smart caching
    if (url.pathname.startsWith('/api/')) {
        console.log('[SW] Intercepting API request:', url.pathname);
        // Check if this is a cacheable API endpoint
        const isCacheable = CACHEABLE_API_PATTERNS.some(pattern => pattern.test(url.pathname));

        if (isCacheable) {
            event.respondWith(networkFirstWithSmartCache(event.request, url));
        } else {
            event.respondWith(networkOnly(event.request));
        }
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

// Network-only strategy (no caching)
async function networkOnly(request) {
    try {
        return await fetch(request);
    } catch (error) {
        return new Response(JSON.stringify({
            error: 'offline',
            detail: 'You are offline and this content is not available.'
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Network-first strategy with smart caching for API calls
async function networkFirstWithSmartCache(request, url) {
    try {
        const response = await fetch(request);

        // Cache successful responses for offline use
        if (response.ok) {
            const cache = await caches.open(CONTENT_CACHE);
            cache.put(request, response.clone());

            console.log('[SW] Caching API response:', url.pathname + url.search);

            // Notify the main thread to also store in IndexedDB for structured queries
            notifyClientToCache(url.pathname + url.search, response.clone());

            // Limit content cache size
            limitCacheSize(CONTENT_CACHE, 200);
        }

        return response;
    } catch (error) {
        // Try to serve from cache when offline
        const cached = await caches.match(request);
        if (cached) {
            // Add offline indicator header
            const headers = new Headers(cached.headers);
            headers.set('X-Offline-Cache', 'true');
            return new Response(cached.body, {
                status: cached.status,
                statusText: cached.statusText,
                headers: headers
            });
        }

        // Return error response
        return new Response(JSON.stringify({
            error: 'offline',
            detail: 'You are offline and this content is not cached.',
            offline: true
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Notify client to cache data in IndexedDB
async function notifyClientToCache(pathname, response) {
    try {
        const clients = await self.clients.matchAll();
        console.log('[SW] notifyClientToCache - clients:', clients.length, 'pathname:', pathname);
        if (clients.length === 0) return;

        const data = await response.json();

        // Determine cache type based on URL pattern
        let cacheType = null;
        let cacheData = null;

        if (pathname.match(/^\/api\/passage\/[^/?]+(\?|$)/)) {
            // Main passage data - cache verses
            cacheType = 'passage';
            cacheData = data;
        } else if (pathname.includes('/interlinear')) {
            // Interlinear data
            cacheType = 'interlinear';
            cacheData = data;
        } else if (pathname.includes('/commentary')) {
            // Commentary data
            cacheType = 'commentary';
            cacheData = data;
        } else if (pathname.includes('/crossrefs')) {
            // Cross-references
            cacheType = 'crossrefs';
            cacheData = data;
        } else if (pathname.match(/^\/api\/word\/[GH]\d+$/)) {
            // Lexicon entry
            cacheType = 'lexicon';
            cacheData = data;
        }

        if (cacheType && cacheData) {
            console.log('[SW] Sending CACHE_DATA message:', cacheType, pathname);
            // Send to first available client
            clients[0].postMessage({
                type: 'CACHE_DATA',
                cacheType: cacheType,
                data: cacheData,
                pathname: pathname
            });
        } else {
            console.log('[SW] No cache type matched for:', pathname);
        }
    } catch (err) {
        // Silent fail - caching is best-effort
        console.warn('[SW] Failed to notify client for caching:', err);
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

// Handle messages from the main thread
self.addEventListener('message', event => {
    const { type, payload } = event.data || {};

    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;

        case 'CLEAR_CACHE':
            // Clear all caches
            caches.keys().then(names => {
                return Promise.all(names.map(name => caches.delete(name)));
            }).then(() => {
                event.ports[0]?.postMessage({ success: true });
            });
            break;

        case 'GET_CACHE_STATS':
            // Return cache statistics
            getCacheStats().then(stats => {
                event.ports[0]?.postMessage(stats);
            });
            break;

        case 'PREFETCH_CHAPTER':
            // Prefetch a chapter for offline use
            if (payload?.book && payload?.chapter) {
                prefetchChapter(payload.book, payload.chapter, payload.translation || 'BSB');
            }
            break;
    }
});

// Get cache statistics
async function getCacheStats() {
    const stats = {
        static: { count: 0 },
        content: { count: 0, urls: [] }
    };

    try {
        const staticCache = await caches.open(STATIC_CACHE);
        const staticKeys = await staticCache.keys();
        stats.static.count = staticKeys.length;

        const contentCache = await caches.open(CONTENT_CACHE);
        const contentKeys = await contentCache.keys();
        stats.content.count = contentKeys.length;
        stats.content.urls = contentKeys.slice(0, 20).map(r => r.url);
    } catch (err) {
        console.error('Failed to get cache stats:', err);
    }

    return stats;
}

// Prefetch a chapter for offline use
async function prefetchChapter(book, chapter, translation) {
    const baseUrl = self.location.origin;
    const ref = encodeURIComponent(`${book} ${chapter}`);

    const urls = [
        `${baseUrl}/api/passage/${ref}?translation=${translation}`,
        `${baseUrl}/api/passage/${ref}/interlinear?translation=${translation}`,
        `${baseUrl}/api/passage/${ref}/commentary`
    ];

    const cache = await caches.open(CONTENT_CACHE);

    for (const url of urls) {
        try {
            const response = await fetch(url);
            if (response.ok) {
                await cache.put(url, response);
            }
        } catch (err) {
            // Continue with other URLs
            console.warn(`Failed to prefetch ${url}:`, err);
        }
    }
}
