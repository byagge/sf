const CACHE_NAME = 'smart-factory-v2';
const urlsToCache = [
  '/orders/plans/master/',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/employee_tasks/tasks/',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    ))
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  // Кэшируем API и страницы
  if (
    request.method === 'GET' && (
      url.pathname.startsWith('/orders/api/stages/') ||
      url.pathname.startsWith('/api/workshops/api/my-workshops/') ||
      url.pathname.startsWith('/api/workshops/api/employees/') ||
      url.pathname === '/employee_tasks/tasks/'
    )
  ) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const respClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, respClone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }
  // Для shell — прежнее поведение
  event.respondWith(
    caches.match(request).then(response => {
      return response || fetch(request);
    })
  );
}); 