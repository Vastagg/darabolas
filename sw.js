// Hálózat először (így a frissítés és a friss árlista azonnal megjön),
// internet nélkül a mentett másolat. Az árlistánál jelezzük, ha a mentett
// másolatból jön, hogy a program „legutolsó ismert árként” mutassa.
const CACHE = 'femdarab-v3';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'prices.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req)
      .then(res => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true }).then(r => {
        if (!r) return caches.match('./');
        if (!req.url.includes('prices.json')) return r;
        const h = new Headers(r.headers);
        h.set('x-offline', '1');
        return r.blob().then(b => new Response(b, { status: 200, headers: h }));
      }))
  );
});
