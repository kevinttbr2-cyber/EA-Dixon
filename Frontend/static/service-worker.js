// ============================
// SERVICE WORKER SIMPLIFICADO
// ============================
const CACHE_NAME = 'dixon-v1';
const urlsToCache = ['/', '/estado', '/static/theme.css'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

// ✅ PUSH
self.addEventListener('push', function(event) {
    let data = {};
    try {
        if (event.data) data = event.data.json();
    } catch (e) {
        data = { title: 'Dixon', body: 'Nueva notificación' };
    }
    const options = {
        body: data.body || 'Nueva notificación',
        icon: '/static/theme.css',
        vibrate: [200, 100, 200],
        data: { url: data.url || '/estado' }
    };
    event.waitUntil(
        self.registration.showNotification(data.title || '📌 Dixon', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data.url || '/estado'));
});

// ✅ FETCH
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
