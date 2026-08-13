(function () {
  const TOKEN = document.body.dataset.token;
  const VAPID_KEY = document.body.dataset.vapidKey;
  const API = `/api/t/${TOKEN}`;

  let fichas = [];
  let fichaAbertaId = null;
  // O nome do técnico vem junto com a lista de fichas e é usado no aviso de
  // "a caminho". Guardar evita ter que buscar de novo — e faz o aviso
  // funcionar mesmo quando a leitura veio do cache offline.
  let tecnicoNome = '';
  // Pontos da ficha que está aberta na tela. O aviso "a caminho" precisa do
  // cliente e do endereço, e lê daqui em vez de bater no servidor de novo.
  let servicosAbertos = [];

  function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2200);
  }

  // Guarda se a última leitura veio do cache offline e de quando ela é.
  // Fica fora do api() porque quem renderiza precisa saber, e o api() só
  // devolve o corpo já parseado.
  let ultimaLeituraOffline = null;

  async function api(path, opts = {}) {
    const resp = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });

    const ehLeitura = !opts.method || opts.method.toUpperCase() === 'GET';
    if (ehLeitura) {
      ultimaLeituraOffline = resp.headers.get('X-Offline')
        ? resp.headers.get('X-Capturado-Em')
        : null;
    }

    const dados = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(dados.erro || 'Erro inesperado');
    return dados;
  }

  // ===== FILA DE SINCRONIZACAO =====
  // Sem sinal, "marcar feito" não pode simplesmente falhar: o técnico está
  // com o cliente na frente e não vai voltar depois para reapertar. A ação
  // entra numa fila e sobe quando o sinal voltar.
  //
  // Reenviar é seguro porque as duas operações da fila são idempotentes:
  // gravar status 'concluido' duas vezes dá no mesmo resultado. Se não
  // fossem, uma fila cega como esta seria perigosa.
  const CHAVE_FILA = `portotec:fila:${TOKEN}`;

  function lerFila() {
    try { return JSON.parse(localStorage.getItem(CHAVE_FILA)) || []; }
    catch { return []; }
  }

  function gravarFila(fila) {
    localStorage.setItem(CHAVE_FILA, JSON.stringify(fila));
    atualizarAvisoTopo();
  }

  function enfileirar(path, opts) {
    const fila = lerFila();
    fila.push({ path, opts, quando: new Date().toISOString() });
    gravarFila(fila);
  }

  async function sincronizarFila() {
    let fila = lerFila();
    if (fila.length === 0) return;

    const pendentes = [];
    for (const item of fila) {
      try {
        await fetch(`${API}${item.path}`, {
          headers: { 'Content-Type': 'application/json' },
          ...item.opts,
        });
      } catch {
        pendentes.push(item); // ainda sem rede: devolve para a fila
      }
    }

    gravarFila(pendentes);
    if (pendentes.length === 0 && fila.length > 0) {
      toast(`${fila.length} ação${fila.length !== 1 ? 'ões' : ''} sincronizada${fila.length !== 1 ? 's' : ''}`);
      if (fichaAbertaId !== null) abrirFicha(fichaAbertaId); else carregarFichas();
    }
  }

  // Uma faixa no topo dizendo o que está acontecendo. Cache silencioso é
  // pior que erro: o técnico agiria sobre dado velho sem desconfiar.
  function atualizarAvisoTopo() {
    let faixa = document.getElementById('t-aviso-offline');
    const naFila = lerFila().length;

    if (!ultimaLeituraOffline && naFila === 0) {
      if (faixa) faixa.remove();
      return;
    }

    if (!faixa) {
      faixa = document.createElement('div');
      faixa.id = 't-aviso-offline';
      faixa.className = 't-aviso-offline';
      document.body.prepend(faixa);
    }

    const partes = [];
    if (ultimaLeituraOffline) {
      const d = new Date(ultimaLeituraOffline);
      const hora = isNaN(d) ? '?' : d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      partes.push(`Sem conexão · dados de ${hora}`);
    }
    if (naFila > 0) {
      partes.push(`${naFila} ação${naFila !== 1 ? 'ões' : ''} aguardando envio`);
    }
    faixa.textContent = partes.join(' · ');
  }

  function esc(v) {
    if (v === null || v === undefined) return '';
    return String(v).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function fmtKm(v) {
    return (v === null || v === undefined || isNaN(v)) ? '—' : Number(v).toFixed(1);
  }

  async function carregarFichas() {
    const container = document.getElementById('lista-fichas');
    try {
      const dados = await api('/fichas');
      fichas = dados.fichas;
      tecnicoNome = dados.tecnico?.nome || tecnicoNome;

      if (fichas.length === 0) {
        container.innerHTML = `<div class="t-vazio"><h1>Sem rotas por aqui</h1><p>Você ainda não tem nenhuma ficha atribuída.</p></div>`;
        return;
      }

      container.innerHTML = fichas.map((f) => `
        <div class="t-ficha-card ${f.status === 'concluida' ? 'concluida' : ''}" onclick="window._tAbrirFicha(${f.id})">
          <div class="t-ficha-titulo">
            ${esc(f.dia_semana)}
            ${f.status === 'concluida' ? '<span class="t-tag-ok">Concluída</span>' : ''}
          </div>
          <div class="t-ficha-meta">${f.total_servicos} ponto${f.total_servicos !== 1 ? 's' : ''} · ${fmtKm(f.distancia_total)} km</div>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = `<div class="t-vazio"><h1>Falha ao carregar</h1><p>${esc(e.message)}</p></div>`;
    } finally {
      atualizarAvisoTopo();
    }
  }

  async function abrirFicha(fichaId) {
    fichaAbertaId = fichaId;
    const lista = document.getElementById('lista-fichas');
    const detalhe = document.getElementById('detalhe-ficha');
    lista.style.display = 'none';
    detalhe.classList.add('aberto');
    detalhe.innerHTML = `<div class="t-loading">Carregando roteiro...</div>`;

    try {
      const dados = await api(`/fichas/${fichaId}`);
      renderDetalhe(dados.ficha, dados.servicos);
    } catch (e) {
      detalhe.innerHTML = `<div class="t-vazio"><p>${esc(e.message)}</p></div>`;
    } finally {
      atualizarAvisoTopo(); // o api() acabou de dizer se a leitura veio do cache
    }
  }

  function renderDetalhe(ficha, servicos) {
    servicosAbertos = servicos || [];
    const detalhe = document.getElementById('detalhe-ficha');
    const concluida = ficha.status === 'concluida';

    const pontosHtml = servicos.map((s, i) => {
      const feito = s.status === 'concluido';
      const enderecoBusca = encodeURIComponent(s.endereco_completo || s.cep || '');
      const temCoord = s.lat && s.lng;
      const urlMaps = `https://www.google.com/maps/search/?api=1&query=${enderecoBusca}`;
      const urlWaze = temCoord
        ? `https://waze.com/ul?ll=${s.lat},${s.lng}&navigate=yes`
        : `https://waze.com/ul?q=${enderecoBusca}&navigate=yes`;
      return `
        <div class="t-ponto ${feito ? 'concluido' : ''}">
          <div class="t-ponto-num">${i + 1}</div>
          <div class="t-ponto-info">
            <div class="t-ponto-cliente">${esc(s.cliente) || 'Cliente sem nome'}</div>
            <div class="t-ponto-endereco">${esc(s.endereco_completo)}</div>
            ${s.tipo_aparelho ? `<div class="t-ponto-aparelho">${esc(s.tipo_aparelho)}${s.modelo ? ' · ' + esc(s.modelo) : ''}</div>` : ''}
            <div class="t-ponto-acoes">
              <a class="t-ponto-link" target="_blank" rel="noopener" href="${urlMaps}">Google Maps</a>
              <a class="t-ponto-link t-ponto-link-waze" target="_blank" rel="noopener" href="${urlWaze}">Waze</a>
              <button class="t-ponto-link t-ponto-link-aviso" onclick="window._tAvisarACaminho(${s.id})">A caminho</button>
              <button class="t-ponto-check ${feito ? 'concluido' : ''}" onclick="window._tConcluirPonto(${s.id}, '${feito ? 'pendente' : 'concluido'}')">
                ${feito ? 'Concluído' : 'Marcar feito'}
              </button>
            </div>
          </div>
        </div>`;
    }).join('');

    detalhe.innerHTML = `
      <button class="t-voltar" onclick="window._tVoltar()">&larr; Todas as rotas</button>
      <button class="t-acao-rota ${concluida ? 'reabrir' : ''}" onclick="window._tConcluirRota(${ficha.id}, '${ficha.status || 'pendente'}')">
        ${concluida ? 'Reabrir rota' : 'Concluir rota'}
      </button>
      ${pontosHtml || '<div class="t-vazio"><p>Nenhum ponto nessa ficha ainda.</p></div>'}
    `;
  }

  // ===== AVISO "A CAMINHO" NO GRUPO DO WHATSAPP =====
  // A API oficial do WhatsApp (Cloud API da Meta) NAO envia mensagem para
  // grupo — ela existe para conversa empresa/cliente, um a um. Nao e limite de
  // plano, o recurso nao existe. Disparo automatico em grupo so por gateway
  // nao-oficial (Z-API, Evolution), que custa mensalidade e arrisca banir o
  // numero. Enquanto essa decisao nao for tomada, o caminho honesto e este:
  // a mensagem sai pronta e o tecnico so escolhe o grupo e envia.
  //
  // navigator.share abre a bandeja nativa do celular, onde o grupo aparece
  // entre as conversas recentes — um toque. O wa.me e o plano B para desktop,
  // onde a bandeja nativa nao existe.
  function montarAviso(s) {
    const partes = [];
    partes.push(`🚗 Técnico ${tecnicoNome || ''} a caminho do cliente ${s.cliente || 'sem nome'}`.trim());
    if (s.endereco_completo) partes.push(`📍 ${s.endereco_completo}`);
    partes.push(urlWazeDe(s));

    return partes.join('\n\n');
  }

  function urlWazeDe(s) {
    const busca = encodeURIComponent(s.endereco_completo || s.cep || '');
    return (s.lat && s.lng)
      ? `https://waze.com/ul?ll=${s.lat},${s.lng}&navigate=yes`
      : `https://waze.com/ul?q=${busca}&navigate=yes`;
  }

  window._tAvisarACaminho = async function (servicoId) {
    // Procura o ponto na ficha aberta. Os dados ja estao em memoria, entao o
    // aviso funciona sem rede — inclusive quando a leitura veio do cache.
    const s = servicosAbertos.find(x => x.id === servicoId);
    if (!s) { toast('Ponto não encontrado'); return; }

    const texto = montarAviso(s);

    // O Waze passa a ser oferecido ANTES de sair da tela, e nunca sozinho.
    // Na versao anterior eu abria o WhatsApp e logo em seguida navegava para o
    // Waze automaticamente — e a navegacao matava a aba do WhatsApp antes dela
    // aparecer. Sintoma exato relatado pelo Kalebe: "abre so o waze".
    // Agora o Waze e um alvo esperando o toque dele, nunca uma navegacao que
    // atropela o passo anterior.
    oferecerWaze(s);

    if (navigator.share) {
      try {
        await navigator.share({ text: texto });
        return;
      } catch (e) {
        // Desistiu da bandeja: nao insiste abrindo o WhatsApp por outro
        // caminho, que seria forcar o que ele acabou de recusar.
        if (e && e.name === 'AbortError') return;
        // Qualquer outro erro cai no plano B abaixo.
      }
    }

    // Plano B: NAVEGACAO, nao window.open. Pop-up em aba nova e barrado por
    // bloqueador na maioria dos celulares e some sem avisar — foi o que
    // aconteceu. O esquema whatsapp:// abre o aplicativo direto e cai na tela
    // de escolher conversa, onde o grupo esta entre as recentes.
    const appUrl = `whatsapp://send?text=${encodeURIComponent(texto)}`;
    const webUrl = `https://wa.me/?text=${encodeURIComponent(texto)}`;
    const ehCelular = /android|iphone|ipad|ipod/i.test(navigator.userAgent);

    window.location.href = ehCelular ? appUrl : webUrl;
  };

  // Deixa o Waze pronto no rodape para quando o tecnico voltar do WhatsApp.
  // NAO navega sozinho: era isso que atropelava a abertura do WhatsApp. Duas
  // saidas de tela disputando o mesmo toque sempre terminam com uma perdendo,
  // e a que perdia era justamente o aviso ao grupo.
  function oferecerWaze(s) {
    const url = urlWazeDe(s);

    const antiga = document.getElementById('t-abrir-waze');
    if (antiga) antiga.remove();

    const faixa = document.createElement('a');
    faixa.id = 't-abrir-waze';
    faixa.className = 't-abrir-waze';
    faixa.href = url;
    faixa.target = '_blank';
    faixa.rel = 'noopener';
    faixa.innerHTML = `Abrir Waze para ${esc(s.cliente || 'o cliente')} &rarr;`;
    faixa.addEventListener('click', () => faixa.remove());
    document.body.appendChild(faixa);

    // 5 minutos: tempo de mandar a mensagem, escolher o grupo e voltar. Os 45s
    // de antes sumiam antes do tecnico terminar de escrever no WhatsApp.
    setTimeout(() => {
      const atual = document.getElementById('t-abrir-waze');
      if (atual === faixa) faixa.remove();
    }, 300000);
  }

  window._tAbrirFicha = abrirFicha;

  window._tVoltar = function () {
    fichaAbertaId = null;
    document.getElementById('lista-fichas').style.display = '';
    document.getElementById('detalhe-ficha').classList.remove('aberto');
    carregarFichas();
  };

  window._tConcluirRota = async function (fichaId, statusAtual) {
    const novo = statusAtual === 'concluida' ? 'pendente' : 'concluida';
    try {
      await api(`/fichas/${fichaId}/status`, { method: 'PUT', body: JSON.stringify({ status: novo }) });
      toast(novo === 'concluida' ? 'Rota concluída' : 'Rota reaberta');
      abrirFicha(fichaId);
    } catch (e) { toast(e.message); }
  };

  window._tConcluirPonto = async function (servicoId, novoStatus) {
    const opts = { method: 'PUT', body: JSON.stringify({ status: novoStatus }) };
    try {
      await api(`/servicos/${servicoId}/status`, opts);
      toast(novoStatus === 'concluido' ? 'Ponto marcado como feito' : 'Ponto reaberto');
      if (fichaAbertaId) abrirFicha(fichaAbertaId);
    } catch (e) {
      // TypeError do fetch = não saiu do aparelho. Erro do servidor (regra de
      // negócio, 4xx) não vai para a fila: reenviar depois daria o mesmo erro.
      if (e instanceof TypeError || !navigator.onLine) {
        enfileirar(`/servicos/${servicoId}/status`, opts);
        toast('Sem sinal — vai subir quando a conexão voltar');
      } else {
        toast(e.message);
      }
    }
  };

  // ─── Notificações push ──────────────────────────────────────────
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
  }

  async function statusInscricao() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
    const reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  }

  async function atualizarBotaoSino() {
    const btn = document.getElementById('btn-notificacoes');
    const sub = await statusInscricao().catch(() => null);
    btn.classList.toggle('ativo', !!sub);
  }

  async function alternarNotificacoes() {
    if (!VAPID_KEY) { toast('Notificações não configuradas no servidor'); return; }
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      toast('Seu navegador não suporta notificações');
      return;
    }

    const reg = await navigator.serviceWorker.ready;
    const existente = await reg.pushManager.getSubscription();

    if (existente) {
      await api('/push/subscribe', { method: 'DELETE', body: JSON.stringify({ endpoint: existente.endpoint }) }).catch(() => {});
      await existente.unsubscribe();
      toast('Notificações desativadas');
      atualizarBotaoSino();
      return;
    }

    const permissao = await Notification.requestPermission();
    if (permissao !== 'granted') { toast('Permissão negada'); return; }

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_KEY),
    });

    await api('/push/subscribe', {
      method: 'POST',
      body: JSON.stringify({
        endpoint: sub.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode(...new Uint8Array(sub.getKey('p256dh')))),
          auth: btoa(String.fromCharCode(...new Uint8Array(sub.getKey('auth')))),
        },
      }),
    });
    toast('Notificações ativadas');
    atualizarBotaoSino();
  }

  document.getElementById('btn-notificacoes').addEventListener('click', () => {
    alternarNotificacoes().catch((e) => toast(e.message));
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
      .then(() => atualizarBotaoSino())
      .catch(() => {});
  }

  // ===== AUTO-REFRESH =====
  // Mesmo mecanismo do painel: um contador no servidor sobe a cada escrita e
  // aqui só perguntamos se ele mudou. No campo isso importa mais do que no
  // escritório — o técnico não fica olhando a tela esperando para apertar F5,
  // e uma rota alterada que não aparece no celular dele vira viagem perdida.
  //
  // 20s em vez dos 10s do painel: o celular costuma estar em rede móvel, e
  // metade das checagens é metade do consumo de dados e de bateria.
  const INTERVALO_REVISAO = 20000;
  let revisaoConhecida = null;

  async function lerRevisao() {
    const resp = await fetch(`${API}/versao`, { cache: 'no-store' });
    if (!resp.ok) throw new Error('revisão indisponível');
    return (await resp.json()).revisao;
  }

  async function verificarRevisao() {
    if (document.hidden) return;

    let revisao;
    try {
      revisao = await lerRevisao();
    } catch {
      return; // sem sinal no meio da rua é situação esperada, não erro
    }

    if (revisaoConhecida === null) {
      revisaoConhecida = revisao;
      return;
    }
    if (revisao === revisaoConhecida) return;
    revisaoConhecida = revisao;

    // Recarrega exatamente a tela em que o técnico está: se ele abriu uma
    // rota, mantém a rota aberta em vez de jogá-lo de volta para a lista.
    if (fichaAbertaId !== null) {
      await abrirFicha(fichaAbertaId);
    } else {
      await carregarFichas();
    }
    toast('Rota atualizada');
  }

  carregarFichas().then(atualizarAvisoTopo);

  lerRevisao().then((r) => { revisaoConhecida = r; }).catch(() => {});
  setInterval(verificarRevisao, INTERVALO_REVISAO);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) verificarRevisao();
  });

  // A volta do sinal dispara as duas coisas na ordem certa: primeiro sobe o
  // que ficou pendente, depois busca o estado atualizado. Ao contrário, a
  // tela mostraria dados sem as ações que ainda estavam na fila.
  window.addEventListener('online', async () => {
    await sincronizarFila();
    verificarRevisao();
  });
  window.addEventListener('offline', atualizarAvisoTopo);

  sincronizarFila();
})();
