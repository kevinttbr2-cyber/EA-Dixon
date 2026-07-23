// frontend/static/service-worker.js
const CACHE_NAME = 'dixon-v3';

// ✅ ARCHIVOS A CACHEAR (SIN /offline)
const urlsToCache = [
  '/',
  '/static/theme.css',
  '/static/manifest.json',
  '/static/js/imprimir.js',
  '/static/js/imprimir_ticket.js',
  '/static/js/lector.js'
  // ❌ ELIMINAR '/offline'
];
