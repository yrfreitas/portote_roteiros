// Service Worker do Portotec Roteiros.
//
// REGRA DE OURO: nada que venha de /api/* é cacheado, nunca. Isso é uma
// ferramenta operacional — mostrar uma rota desatualizada pro técnico
// por causa de cache é pior do que não ter cache nenhum. Só a "casca"
// do app (HTML/CSS/JS/ícones) é cacheada, pra abrir rápido e funcionar
// com internet ruim; os dados sempre vêm da rede.

// Subir esta versão a cada mudança em app.js/tecnico.js/style.css é
// obrigatório: o activate abaixo apaga todo cache com nome diferente, e é isso
// que força quem já tem o PWA instalado a receber o arquivo novo. Sem o bump,
// o navegador continua servindo o JS antigo do cache indefinidamente.
// v3 = entrada do auto-refresh (verificarRevisao em app.js e tecnico.js).
// v4 = resumo por setor com denominador correto e linha "Sem setor",
//      e rota concluída saindo da sidebar (passa a viver só no Histórico).
// v5 = setor obrigatório, classificação em lote e filtro de período.
// v6 = modo offline de leitura do técnico + fila de sincronização.
// v7 = verificador de encaixe com régua única, motivos e mapa.
// v8 = correção do mapa (setView antes das camadas).
// v9 = simulação "como o dia fica" ao clicar num dia.
// v10 = botão "A caminho" que avisa o grupo do WhatsApp.
// v11 = o Waze abre logo depois do aviso, sem voltar à tela.
// v12 = conserta o WhatsApp que não abria (o Waze atropelava).
// v13 = folha de botões no "A caminho" + selo de versão na tela.
// v14 = botão "A caminho" também no painel, na linha de cada cliente.
// v15 = rastreio ao vivo: o cliente acompanha o técnico a caminho.
// v16 = código do app passa a ser rede-primeiro (fim do JS velho no cache).
// v17 = acompanhamento por previsão de chegada (sem GPS).
// v18 = fichas na ordem da semana e destaque para a rota de hoje.
// v19 = ordem de calendário de verdade (ano, mês, dia).
// v20 = "HOJE" compara a data, não o nome do dia.
// v21 = edição de ficha (dia e data) — antes não existia.
// v22 = baixa da peça no AgoraOS ao vincular na aba Peças.
// v23 = o cliente passa a ver o técnico ANDANDO no mapa, não só a casa dele.
// v24 = GPS retoma ao abrir o app + selo visível de estado (era silêncio).
// v25 = recusa leitura de GPS imprecisa (era ela a "localização aleatória").
// v26 = o celular reporta versão e estado do GPS (fim do diagnóstico às cegas).
// v27 = rastreador nativo (Traccar Client) no lugar do GPS do navegador.
// v28 = foto de perfil do técnico + rastreador separado por técnico.
// v29 = foto aceita HEIC/iPhone + painel se atualiza sozinho.
// v30 = fichas de cada técnico podem ser recolhidas na barra lateral.
// v31 = previsão de chegada calculada da posição REAL do técnico.
// v32 = transferir rota inteira ou ponto avulso entre técnicos.
// v33 = sessão expirada leva ao login + erros do navegador viram registro.
// v34 = aba Diagnóstico, aviso de pontos sem setor e comparativo de técnicos.
// v35 = deploy de verificação (nenhuma mudança de comportamento).
// v36 = login por pessoa com papéis + chat flutuante com o cliente.
// v37 = chat da equipe + apagar conversa de cliente.
// v38 = "ponto de serviço" vira "atendimento técnico" na tela.
// v39 = fim das mensagens duplicadas + site mais rápido (pool, menos tráfego).
// v40 = corrige o 404 que travava a ficha a cada auto-refresh.
// v41 = GPS e chat param de forçar recarga do painel + chat responde na hora.
// v42 = aviso quando o cliente não está vendo o técnico no mapa.
// v43 = verificar CEP só mostra rotas em aberto e de hoje em diante.
// v44 = mover atendimento de dia sem apagar e recriar.
// v45 = reagendar (técnico + dia) num bloco só e mais bonito no modal.
// v46 = verificar CEP agrupado por técnico.
// v47 = um mapa por técnico no verificar CEP, lado a lado.
// v48 = mapas do verificar CEP realmente lado a lado (caixa alargada).
// v49 = nova aba Estoque: saldo, custo médio ponderado, entrada/saída/ajuste,
//       mínimo com alerta e histórico. Saldo controlado no site.
// v50 = estoque com marca/aparelho/modelo/preço, agrupado por aparelho
//       (estilo AgoraOS), filtros por chip e marca, e edição da ficha da peça.
// v51 = "estoque dentro do estoque": prateleiras nomeadas (Electrolux...) que
//       o admin cria e abre para adicionar peças dentro. Navegação em 2 níveis.
// v52 = conserta o clique no card de estoque (aspas do onclick quebravam o
//       HTML): não dava para abrir a prateleira nem adicionar peça dentro.
// v53 = estoque linkado: saída "para" um cliente/atendimento, entrada pela
//       nota fiscal na aba Peças (idempotente) e saldo do estoque na aba Peças.
// v54 = reagendar ganha "criar dia novo" ali mesmo: escolhe a data, cria a
//       ficha do técnico e já a seleciona como destino do atendimento.
// v55 = bipar nota fiscal: lê a chave (leitor de código de barras, câmera ou
//       XML colado), reconhece as peças e manda pro estoque (idempotente).
// v56 = conserta modal alto que não rolava (editar atendimento travava, Salvar
//       fora do alcance); + setor/marca e Nº da OS no adicionar do verificar CEP.
// v57 = bipar não dá mais 502: busca direcionada da nota (acha o e-mail exato)
//       e, se demorar/falhar, pede o XML em vez de estourar o gateway.
// v58 = conserta o select de Setor vazio no adicionar do verificar CEP
//       (preenche depois de montar o form, carregando os setores se preciso).
// v59 = bipar mais robusto: busca da nota sempre volta com status (nunca 502),
//       varredura só dos e-mails recentes, e mostra o motivo do erro na tela.
// v60 = sub-estoque dentro do estoque (Panasonic > Geladeira): navegação em
//       árvore, roll-up dos totais e exclusão que promove os filhos.
// v61 = peça só entra em sub-estoque (topo só cria sub-estoque) + botão de
//       excluir peça do estoque.
// v62 = bipar: escolher o destino navegando (clica Panasonic > Geladeira) em
//       vez de um menu suspenso; só guarda em sub-estoque.
// v63 = permissões granulares por usuário (editor em drawer no Acessos) +
//       diagnóstico editável (status/observação/excluir nos erros da tela).
const CACHE_VERSAO = 'portotec-roteiros-v63';

const ARQUIVOS_CASCA = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/logo.png',
  '/static/manifest.json',
  '/static/tecnico.css',
  '/static/tecnico.js',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE_VERSAO)
      .then((cache) => cache.addAll(ARQUIVOS_CASCA))
      .then(() => self.skipWaiting())
  );
});

// Cache separado e de nome FIXO para o modo offline do técnico. Fica de fora
// da limpeza do activate de propósito: se ele fosse apagado a cada deploy, o
// técnico que abrisse o app sem sinal logo depois de uma atualização ficaria
// sem nada — justamente o cenário que este cache existe para cobrir.
const CACHE_OFFLINE = 'portotec-tecnico-offline';

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(
        nomes
          .filter((nome) => nome !== CACHE_VERSAO && nome !== CACHE_OFFLINE)
          .map((nome) => caches.delete(nome))
      )
    ).then(() => self.clients.claim())
  );
});

// Leitura do técnico: rede primeiro, cache só quando a rede falha.
//
// A regra "nunca cachear /api/" continua valendo para o painel e para toda
// escrita — mostrar rota desatualizada como se fosse atual é pior que não
// mostrar nada. O que muda aqui é que a resposta guardada volta MARCADA como
// offline, e a tela avisa de quando ela é. Um técnico que sabe que está vendo
// a foto das 07h40 consegue trabalhar; um que não sabe, não.
async function redeComQuedaParaCache(request) {
  try {
    const resposta = await fetch(request);
    if (resposta.ok) {
      const clone = resposta.clone();
      const corpo = await clone.blob();
      const cabecalhos = new Headers(clone.headers);
      cabecalhos.set('X-Capturado-Em', new Date().toISOString());
      const cache = await caches.open(CACHE_OFFLINE);
      await cache.put(request, new Response(corpo, { status: 200, headers: cabecalhos }));
    }
    return resposta;
  } catch (erroDeRede) {
    const cache = await caches.open(CACHE_OFFLINE);
    const cacheado = await cache.match(request);
    if (!cacheado) throw erroDeRede;

    const corpo = await cacheado.blob();
    const cabecalhos = new Headers(cacheado.headers);
    cabecalhos.set('X-Offline', '1');
    return new Response(corpo, { status: 200, headers: cabecalhos });
  }
}

self.addEventListener('fetch', (evento) => {
  const url = new URL(evento.request.url);

  // API: sempre rede, nunca cache — com uma exceção medida.
  if (url.pathname.startsWith('/api/')) {
    // Só GET das rotas do técnico entra no fallback offline. Escrita nunca:
    // devolver do cache um "concluir ponto" daria ao técnico a impressão de
    // que gravou quando nada saiu do celular. E /versao fica de fora porque
    // servir revisão velha faria o auto-refresh achar que nada mudou.
    const leituraDoTecnico = evento.request.method === 'GET'
      && url.pathname.startsWith('/api/t/')
      && !url.pathname.endsWith('/versao');

    if (leituraDoTecnico) {
      evento.respondWith(redeComQuedaParaCache(evento.request));
    } else {
      evento.respondWith(fetch(evento.request));
    }
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

  // CÓDIGO DO APP: rede primeiro, cache só como rede de segurança.
  //
  // Isto era cache-first ("stale-while-revalidate") e custou caro: o navegador
  // servia o JS velho e só buscava o novo depois, então TODA correção só
  // aparecia na segunda abertura. Em 2026-08-13 o técnico testou um botão
  // novo três vezes e continuou rodando a versão antiga — o diagnóstico
  // mostrou zero rastreios criados enquanto a API funcionava perfeitamente.
  //
  // Para HTML/JS/CSS, servir versão velha não é "um pouco desatualizado": é o
  // aplicativo errado. Estes arquivos são pequenos e a rede resolve em
  // milissegundos; o cache continua ali para quando não houver rede.
  const ehCodigoDoApp = /\.(js|css)$/.test(url.pathname) || url.pathname === '/'
    || url.pathname.startsWith('/tecnico/');

  if (ehCodigoDoApp) {
    evento.respondWith(
      fetch(evento.request).then((resposta) => {
        if (resposta.ok) {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
        }
        return resposta;
      }).catch(() => caches.match(evento.request))
    );
    return;
  }

  // Demais estáticos (ícones, imagens, manifest): cache primeiro, atualiza em
  // segundo plano. Esses raramente mudam e não alteram comportamento.
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

// Notificação de rota nova atribuída — o payload vem do backend em
// services/push.py, formato {titulo, corpo, url}.
self.addEventListener('push', (evento) => {
  let dados = { titulo: 'Portotec', corpo: 'Você tem uma atualização.', url: '/' };
  try { dados = { ...dados, ...evento.data.json() }; } catch (e) { /* payload vazio, usa default */ }

  evento.waitUntil(
    self.registration.showNotification(dados.titulo, {
      body: dados.corpo,
      icon: '/static/assets/android-chrome-192x192.png',
      badge: '/static/assets/favicon-32x32.png',
      data: { url: dados.url },
    })
  );
});

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const alvo = evento.notification.data?.url || '/';
  evento.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((janelas) => {
      for (const janela of janelas) {
        if (janela.url.includes(alvo) && 'focus' in janela) return janela.focus();
      }
      return self.clients.openWindow(alvo);
    })
  );
});
