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

  // Dia de hoje por extenso, no mesmo texto que o banco guarda. O toLocaleDateString
  // devolve "segunda-feira" em minusculo — daí o ajuste da primeira letra.
  function diaDeHoje() {
    const d = new Date().toLocaleDateString('pt-BR', { weekday: 'long' });
    return d.charAt(0).toUpperCase() + d.slice(1);
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

      const hoje = diaDeHoje();
      container.innerHTML = fichas.map((f) => `
        <div class="t-ficha-card ${f.status === 'concluida' ? 'concluida' : ''} ${f.dia_semana === hoje ? 'hoje' : ''}" onclick="window._tAbrirFicha(${f.id})">
          <div class="t-ficha-titulo">
            ${esc(f.dia_semana)}
            ${f.dia_semana === hoje ? '<span class="t-tag-hoje">HOJE</span>' : ''}
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
      const urlMaps = `https://www.google.com/maps/search/?api=1&query=${enderecoBusca}`;
      // A URL do Waze nao e montada aqui: o botao passa pelo aviso primeiro, e
      // quem gera o link e o urlWazeDe(), fonte unica para mensagem e botao.
      return `
        <div class="t-ponto ${feito ? 'concluido' : ''}">
          <div class="t-ponto-num">${i + 1}</div>
          <div class="t-ponto-info">
            <div class="t-ponto-cliente">${esc(s.cliente) || 'Cliente sem nome'}</div>
            <div class="t-ponto-endereco">${esc(s.endereco_completo)}</div>
            ${s.tipo_aparelho ? `<div class="t-ponto-aparelho">${esc(s.tipo_aparelho)}${s.modelo ? ' · ' + esc(s.modelo) : ''}</div>` : ''}
            <div class="t-ponto-acoes">
              <a class="t-ponto-link" target="_blank" rel="noopener" href="${urlMaps}">Google Maps</a>
              <button class="t-ponto-link t-ponto-link-waze" onclick="window._tAvisarACaminho(${s.id})">Waze</button>
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
  function montarAviso(s, linkAcompanhar) {
    const partes = [];
    partes.push(`🚗 Técnico ${tecnicoNome || ''} a caminho do cliente ${s.cliente || 'sem nome'}`.trim());
    if (s.endereco_completo) partes.push(`📍 ${s.endereco_completo}`);
    // O link de acompanhamento vem primeiro entre os dois: é o que interessa a
    // quem recebe. O do Waze fica como referência do destino.
    if (linkAcompanhar) partes.push(`Acompanhe ao vivo:\n${linkAcompanhar}`);
    partes.push(urlWazeDe(s));

    return partes.join('\n\n');
  }

  // ===== LINK DE ACOMPANHAMENTO =====
  // Sem GPS, de proposito: pagina web nao recebe localizacao em segundo plano.
  // Assim que o tecnico sai para o Waze o sistema congela a pagina e o
  // watchPosition para. O acompanhamento e por PREVISAO de chegada, calculada
  // no servidor — nao depende de permissao nem de o app ficar aberto.
  async function criarLinkAcompanhamento(servicoId) {
    try {
      const r = await api(`/servicos/${servicoId}/rastreio`, { method: 'POST' });
      return `${location.origin}/acompanhar/${r.token}`;
    } catch (e) {
      // Sem o link a mensagem ainda vale. Avisar sem acompanhamento e melhor
      // do que nao avisar.
      console.warn('Nao consegui criar o link:', e.message);
      return null;
    }
  }

  // Duas tentativas de disparar o WhatsApp automaticamente falharam no celular
  // do Kalebe — pop-up barrado numa, navegacao atropelada na outra. O problema
  // de fundo e sempre o mesmo: acao programatica que sai da tela depende de
  // permissao do navegador, varia por aparelho e falha em SILENCIO.
  //
  // Toque de verdade em link nao depende de permissao nenhuma. Entao a tela
  // para de adivinhar e passa a oferecer os alvos: ele toca, e funciona em
  // qualquer aparelho. Custa um toque a mais e nunca falha calada.
  window._tAvisarACaminho = async function (servicoId) {
    const s = servicosAbertos.find(x => x.id === servicoId);
    if (!s) { toast('Ponto não encontrado'); return; }

    // O rastreio comeca ANTES de montar a mensagem, porque o link dele entra
    // no texto. Se falhar, segue sem o link — avisar o cliente sem
    // acompanhamento e melhor que nao avisar.
    const linkAcompanhar = await criarLinkAcompanhamento(servicoId);

    const texto = montarAviso(s, linkAcompanhar);
    const ehCelular = /android|iphone|ipad|ipod/i.test(navigator.userAgent);
    // whatsapp:// abre o app direto na tela de escolher conversa (o grupo fica
    // entre as recentes). No desktop esse esquema nao existe, entao vai wa.me.
    const urlWhats = ehCelular
      ? `whatsapp://send?text=${encodeURIComponent(texto)}`
      : `https://wa.me/?text=${encodeURIComponent(texto)}`;

    const folha = document.createElement('div');
    folha.className = 't-folha-fundo';
    folha.innerHTML = `
      <div class="t-folha">
        <div class="t-folha-titulo">Avisar que está a caminho</div>
        <pre class="t-folha-msg">${esc(texto)}</pre>
        <a class="t-folha-btn whats" href="${esc(urlWhats)}" target="_blank" rel="noopener">Enviar no WhatsApp</a>
        <button type="button" class="t-folha-btn copiar">Copiar mensagem</button>
        <a class="t-folha-btn waze" href="${esc(urlWazeDe(s))}" target="_blank" rel="noopener">Abrir Waze</a>
        <button type="button" class="t-folha-btn fechar">Fechar</button>
      </div>`;

    const fechar = () => folha.remove();
    folha.addEventListener('click', (e) => { if (e.target === folha) fechar(); });
    folha.querySelector('.fechar').addEventListener('click', fechar);

    // Depois de tocar no WhatsApp, o Waze ganha destaque — a ordem real e
    // avisar e depois dirigir, e a folha continua aberta quando ele voltar.
    folha.querySelector('.whats').addEventListener('click', () => {
      setTimeout(() => {
        if (folha.isConnected) folha.querySelector('.waze').classList.add('destaque');
      }, 400);
    });

    // Copiar e a ultima garantia: se nenhum link abrir no aparelho dele, ainda
    // da para colar no WhatsApp a mao. Nunca fica sem saida.
    folha.querySelector('.copiar').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(texto);
        toast('Mensagem copiada');
      } catch {
        const campo = document.createElement('textarea');
        campo.value = texto;
        document.body.appendChild(campo);
        campo.select();
        try { document.execCommand('copy'); toast('Mensagem copiada'); }
        catch { toast('Não consegui copiar — selecione o texto acima'); }
        campo.remove();
      }
    });

    document.body.appendChild(folha);
  };


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

  // Selo de versão no rodapé. Sem ele não há como saber, olhando o celular do
  // técnico, se o código novo chegou ou se o service worker ainda está
  // servindo o antigo do cache — e sem essa resposta qualquer diagnóstico de
  // "não está indo" vira adivinhação. Subir junto com o CACHE_VERSAO do sw.js.
  const VERSAO_TELA = 'v19';

  (function marcarVersao() {
    const selo = document.createElement('div');
    selo.className = 't-selo-versao';
    selo.textContent = VERSAO_TELA;
    document.body.appendChild(selo);
  })();

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
