const CACHE_NAME = 'dixon-v1';
const urlsToCache = ['/', '/estado', '/static/theme.css'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
    self.skipWaiting();
});

self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
// ============================
// SERVICE WORKER CON NOTIFICACIONES PUSH
// ============================
const CACHE_NAME = 'dixon-cache-v1';
const urlsToCache = [
    '/',
    '/estado',
    '/static/theme.css',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',
    '/offline'
];

// Instalación
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())
    );
});

// Activación
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// ✅ RECIBIR NOTIFICACIONES PUSH
self.addEventListener('push', function(event) {
    let data = {};
    
    try {
        if (event.data) {
            data = event.data.json();
        }
    } catch (e) {
        data = { title: 'Dixon', body: 'Nueva notificación' };
    }
    
    const options = {
        body: data.body || 'Nueva notificación',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        vibrate: [200, 100, 200, 100, 200],
        tag: data.tag || 'default',
        data: {
            url: data.url || '/estado',
            id: data.id || null
        },
        actions: [
            {
                action: 'ver',
                title: '📋 Ver'
            },
            {
                action: 'cerrar',
                title: '❌ Cerrar'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || '📌 Dixon', options)
    );
});

// ✅ CLIC EN NOTIFICACIÓN
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    if (event.action === 'cerrar') {
        return;
    }
    
    const url = event.notification.data.url || '/estado';
    const id = event.notification.data.id;
    
    if (id) {
        event.waitUntil(
            clients.openWindow(`${url}?id=${id}`)
        );
    } else {
        event.waitUntil(
            clients.openWindow(url)
        );
    }
});

// Fetch para offline
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
            .catch(() => caches.match('/offline'))
    );
});
