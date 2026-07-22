// frontend/static/service-worker.js
const CACHE_NAME = 'dixon-v3';

// ✅ ARCHIVOS A CACHEAR (INCLUYENDO LOS DE IMPRESIÓN)
const urlsToCache = [
  '/',
  '/static/theme.css',
  '/static/manifest.json',
  '/static/js/imprimir.js',
  '/static/js/imprimir_ticket.js',
  '/offline'
];

// INSTALACIÓN
self.addEventListener('install', function(event) {
  console.log('🔧 Service Worker instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('✅ Cache abierto');
        return cache.addAll(urlsToCache).catch(function(err) {
          console.warn('⚠️ Error cacheando algunos archivos:', err);
          return Promise.all(
            urlsToCache.map(function(url) {
              return cache.add(url).catch(function(e) {
                console.warn('⚠️ No se pudo cachear:', url, e);
              });
            })
          );
        });
      })
      .then(function() {
        return self.skipWaiting();
      })
  );
});

// ACTIVACIÓN
self.addEventListener('activate', function(event) {
  console.log('🔧 Service Worker activando...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Eliminando cache antiguo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// FETCH
self.addEventListener('fetch', function(event) {
  // No interceptar llamadas a la API ni al backend
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('.railway.app') ||
      event.request.url.includes('chrome-extension')) {
    return;
  }

  // Estrategia: Cache First para assets estáticos
  if (event.request.url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then(function(response) {
          if (response) {
            return response;
          }
          return fetch(event.request).then(function(res) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
            return res;
          });
        })
    );
    return;
  }

  // Estrategia: Network First para páginas HTML
  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(function() {
        return caches.match(event.request)
          .then(function(response) {
            if (response) {
              return response;
            }
            return caches.match('/offline');
          });
      })
  );
});

// ✅ RECIBIR NOTIFICACIONES PUSH
self.addEventListener('push', function(event) {
  if (!event.data) {
    console.warn('⚠️ Push sin datos');
    return;
  }

  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'Notificación',
      icon: '/static/images/icon-192.png',
      badge: '/static/images/icon-192.png',
      vibrate: [200, 100, 200],
      data: {
        url: data.url || '/estado',
        id: data.id || null
      },
      actions: [
        {
          action: 'open',
          title: 'Ver'
        },
        {
          action: 'close',
          title: 'Cerrar'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(
        data.title || 'Dixon Electricidad',
        options
      )
    );
  } catch (error) {
    console.error('❌ Error procesando push:', error);
    const options = {
      body: event.data.text() || 'Nueva notificación',
      icon: '/static/images/icon-192.png',
      badge: '/static/images/icon-192.png'
    };
    event.waitUntil(
      self.registration.showNotification('Dixon', options)
    );
  }
});

// ✅ CLICK EN NOTIFICACIÓN
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data?.url || '/estado';
  const id = event.notification.data?.id || null;

  let finalUrl = url;
  if (id) {
    finalUrl = url.includes('?') ? `${url}&id=${id}` : `${url}?id=${id}`;
  }

  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    })
    .then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url.includes(finalUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(finalUrl);
      }
    })
  );
});
