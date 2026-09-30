/**
 * Service Worker para Sintel PWA
 * Estrategia: network-first para navegacion (documento HTML) y API,
 * cache-first solo para assets estaticos reales (imagenes/fuentes/JS/CSS).
 *
 * [FIX 2026-09-16, auditoria de coherencia de rutas] Bug real encontrado: la
 * version anterior trataba CUALQUIER request no-API como "asset estatico" y
 * lo servia cache-first -- eso incluye la navegacion misma (`/`, `/tienda`,
 * `/alquiler`, `/servicios`, etc.). Un Service Worker con ese cache activo en
 * el navegador de un usuario puede seguir sirviendo una version vieja de la
 * SPA (bundle JS/rutas viejas) indefinidamente, incluso despues de que el
 * codigo cambio -- exactamente el sintoma real reportado ("no redirecciona a
 * tienda/renting/servicios" en un navegador con uso previo, mientras un
 * navegador limpio SI navegaba bien, confirmado con Playwright). Este archivo
 * no se registra hoy desde ningun punto de entrada de la app (`pwa.js::
 * registerServiceWorker()` existe pero no se llama desde `main.js`) -- pero
 * SI hubo un commit historico (674dff8, 2026-07-29) que documentaba esta
 * funcionalidad como activa, asi que un navegador que visito este proyecto en
 * ese periodo puede tener un Service Worker de origen `localhost:5173` (o el
 * dominio real) todavia registrado y sirviendo cache vieja -- el fix de
 * codigo no llega a un Service Worker YA registrado en un navegador; ver
 * AUDITORIA/HOME_URL_ROUTING_AUDIT.md para el paso manual de limpieza.
 */

const CACHE_NAME = 'sintel-v2';
const CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// Rutas que siempre deben ir a red
const NETWORK_ROUTES = [
  '/api/',
  '/renting/equipment',
];

self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(CACHE_URLS).catch(err => {
        console.log('Cache addAll error:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;

  // Skip no-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Navegacion (documento HTML de cualquier ruta, incluye `/`, `/tienda`,
  // `/alquiler`, `/servicios`, cualquier deep-link) -- SIEMPRE network-first.
  // Nunca debe servirse cache-first: es lo que carga el bundle JS/rutas
  // reales del router, tiene que ser siempre la version mas nueva posible.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const cache = caches.open(CACHE_NAME);
            cache.then(c => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => caches.match(request).then(cached => cached || caches.match('/')))
    );
    return;
  }

  // API requests: network-first, fallback to cache
  if (NETWORK_ROUTES.some(route => request.url.includes(route))) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const cache = caches.open(CACHE_NAME);
            cache.then(c => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then(cached => {
            return cached || new Response('Offline - No cached data', { status: 503 });
          });
        })
    );
  } else {
    // Static assets: cache-first, fallback to network
    event.respondWith(
      caches.match(request).then(cached => {
        return (
          cached ||
          fetch(request)
            .then(response => {
              if (response.ok) {
                const cache = caches.open(CACHE_NAME);
                cache.then(c => c.put(request, response.clone()));
              }
              return response;
            })
            .catch(() => {
              return new Response('Resource not found', { status: 404 });
            })
        );
      })
    );
  }
});

// Handle push notifications
self.addEventListener('push', event => {
  const data = event.data?.json() ?? {};
  const title = data.title || 'Sintel';
  const options = {
    body: data.body || 'Nueva notificación',
    icon: '/logo-192.png',
    badge: '/logo-192.png',
    tag: data.tag || 'notification',
    requireInteraction: data.requireInteraction ?? false,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      if (windowClients.length > 0) {
        windowClients[0].focus();
      } else {
        clients.openWindow(event.notification.data?.url || '/');
      }
    })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-reservations') {
    event.waitUntil(syncReservations());
  }
});

async function syncReservations() {
  try {
    const db = await openIDB();
    const reservations = await db.getAll('pending-reservations');

    for (const reservation of reservations) {
      const response = await fetch('/api/reservations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reservation),
      });

      if (response.ok) {
        await db.delete('pending-reservations', reservation.id);
      }
    }
  } catch (error) {
    console.error('Background sync error:', error);
    throw error; // Retry
  }
}

function openIDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('sintel', 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pending-reservations')) {
        db.createObjectStore('pending-reservations', { keyPath: 'id' });
      }
    };
  });
}
