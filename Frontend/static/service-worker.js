// frontend/static/service-worker.js

// ✅ NOMBRE DEL CACHE
const CACHE_NAME = 'dixon-v2';

// ✅ ARCHIVOS A CACHEAR
const urlsToCache = [
  '/',
  '/static/theme.css',
  '/static/manifest.json',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png',
  '/offline'
];

// ============================
// INSTALACIÓN
// ============================
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('✅ Cache abierto');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        return self.skipWaiting();
      })
  );
});

// ============================
// ACTIVACIÓN
// ============================
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

// ============================
// FETCH (CON FALLBACK A OFFLINE)
// ============================
self.addEventListener('fetch', function(event) {
  // ✅ NO interceptar llamadas a la API del backend
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('.railway.app')) {
    return; // Dejar que el navegador maneje la solicitud
  }

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Guardar en cache solo respuestas exitosas
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(function() {
        // Si falla, buscar en cache
        return caches.match(event.request)
          .then(function(response) {
            if (response) {
              return response;
            }
            // Si no está en cache, mostrar offline.html
            return caches.match('/offline');
          });
      })
  );
});

// ============================
// RECIBIR NOTIFICACIONES PUSH
// ============================
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
        id: data.id || null,
        dateOfArrival: Date.now()
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
    
    // Fallback para notificaciones sin JSON
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

// ============================
// CLICK EN NOTIFICACIÓN
// ============================
self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const url = event.notification.data?.url || '/estado';
  const id = event.notification.data?.id || null;

  // Si tiene ID, agregar a la URL
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
      // Buscar una ventana ya abierta
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url.includes(finalUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      // Si no hay ventana abierta, abrir una nueva
      if (clients.openWindow) {
        return clients.openWindow(finalUrl);
      }
    })
  );
});

// ============================
// MANEJO DE ERRORES DE PUSH
// ============================
self.addEventListener('pushsubscriptionchange', function(event) {
  console.log('🔄 Suscripción push cambiada');
  
  event.waitUntil(
    self.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(
        '{{ vapid_public_key }}'
      )
    })
    .then(function(subscription) {
      // Reportar nueva suscripción al servidor
      return fetch('/api/guardar_suscripcion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });
    })
  );
});

// ============================
// FUNCIÓN AUXILIAR - CONVERTIR BASE64 A Uint8Array
// ============================
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
