// Service Worker do Portotec Roteiros.
//
// REGRA DE OURO: nada que venha de /api/* é cacheado, nunca. Isso é uma
// ferramenta operacional — mostrar uma rota desatualizada pro técnico
// por causa de cache é pior do que não ter cache nenhum. Só a "casca"
// do app (HTML/CSS/JS/ícones) é cacheada, pra abrir rápido e funcionar
// com internet ruim; os dados sempre vêm da rede.

const CACHE_VERSAO = 'portotec-roteiros-v1';

const ARQUIVOS_CASCA = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/logo.png',
  '/static/manifest.json',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE_VERSAO)
      .then((cache) => cache.addAll(ARQUIVOS_CASCA))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(
        nomes
          .filter((nome) => nome !== CACHE_VERSAO)
          .map((nome) => caches.delete(nome))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  const url = new URL(evento.request.url);

  // API: sempre rede, nunca cache. Ponto final.
  if (url.pathname.startsWith('/api/')) {
    evento.respondWith(fetch(evento.request));
    return;
  }

  // CDN de terceiros (Leaflet, SortableJS): URLs versionadas na própria
  // string (ex: leaflet@1.9.4) nunca mudam de conteúdo — cache-first
  // é seguro e acelera bastante o carregamento.
  if (url.origin !== self.location.origin) {
    evento.respondWith(
      caches.match(evento.request).then((cacheado) => {
        if (cacheado) return cacheado;
        return fetch(evento.request).then((resposta) => {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
          return resposta;
        });
      })
    );
    return;
  }

  // Casca do app: cache primeiro, atualiza em segundo plano (stale-while-revalidate).
  evento.respondWith(
    caches.match(evento.request).then((cacheado) => {
      const buscaRede = fetch(evento.request).then((resposta) => {
        if (resposta.ok) {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
        }
        return resposta;
      }).catch(() => cacheado);

      return cacheado || buscaRede;
    })
  );
});
