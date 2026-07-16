// frontend/static/service-worker.js
const CACHE_NAME = 'dixon-v2';

// ✅ ARCHIVOS A CACHEAR (SOLO LOS QUE EXISTEN)
const urlsToCache = [
  '/',
  '/static/theme.css',
  '/static/manifest.json',
  '/offline'
  // ❌ ELIMINA imágenes que no existen
  // '/static/images/icon-192.png',
  // '/static/images/icon-512.png'
];

// INSTALACIÓN
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('✅ Cache abierto');
        // ✅ Intentar cachear, pero no fallar si algún archivo no existe
        return cache.addAll(urlsToCache).catch(function(err) {
          console.warn('⚠️ Error cacheando algunos archivos:', err);
          // Intentar cachear uno por uno
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
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('.railway.app')) {
    return;
  }

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
      icon: '/static/theme.css', // ✅ Usar un archivo que existe
      badge: '/static/theme.css',
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
      icon: '/static/theme.css',
      badge: '/static/theme.css'
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
