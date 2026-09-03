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

  // Data de hoje como "AAAA-MM-DD" no fuso LOCAL. O toISOString devolveria UTC
  // e, das 21h em diante no Brasil, marcaria a ficha do dia seguinte como hoje.
  function dataDeHoje() {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
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

      const hoje = dataDeHoje();
      container.innerHTML = fichas.map((f) => `
        <div class="t-ficha-card ${f.status === 'concluida' ? 'concluida' : ''} ${f.data_referencia === hoje ? 'hoje' : ''}" onclick="window._tAbrirFicha(${f.id})">
          <div class="t-ficha-titulo">
            ${esc(f.dia_semana)}
            ${f.data_referencia === hoje ? '<span class="t-tag-hoje">HOJE</span>' : ''}
            ${f.status === 'concluida' ? '<span class="t-tag-ok">Concluída</span>' : ''}
          </div>
          <div class="t-ficha-meta">${f.total_servicos} atendimento${f.total_servicos !== 1 ? 's' : ''} · ${fmtKm(f.distancia_total)} km</div>
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
          <!-- O NÚMERO é o gatilho do desfecho. É o alvo que a mão do técnico
               já procura ao chegar no ponto, e fica no topo do cartão, longe
               dos links de navegação — não dá para tocar sem querer. -->
          <button class="t-ponto-num ${feito ? 'concluido' : ''}"
                  onclick="${feito
                    ? `window._tConcluirPonto(${s.id}, 'pendente')`
                    : `window._tAbrirDesfecho(${s.id})`}"
                  title="${feito ? 'Reabrir atendimento' : 'Registrar o que aconteceu'}"
                  aria-label="${feito ? 'Reabrir atendimento' : 'Concluir atendimento'}">
            ${feito ? '✓' : i + 1}
          </button>
          <div class="t-ponto-info">
            <div class="t-ponto-cliente">${esc(s.cliente) || 'Cliente sem nome'}</div>
            <div class="t-ponto-endereco">${esc(s.endereco_completo)}</div>
            ${s.tipo_aparelho ? `<div class="t-ponto-aparelho">${esc(s.tipo_aparelho)}${s.modelo ? ' · ' + esc(s.modelo) : ''}</div>` : ''}
            ${feito && s.desfecho ? selo_desfecho(s) : ''}
            <div class="t-ponto-acoes">
              <a class="t-ponto-link" target="_blank" rel="noopener" href="${urlMaps}">Google Maps</a>
              <button class="t-ponto-link t-ponto-link-waze" onclick="window._tAvisarACaminho(${s.id})">Waze</button>
              ${!feito ? _botaoComandoVoz(s.id) : ''}
              <!-- Mesma ação do número, com o rótulo escrito: o círculo sozinho
                   pode não ser óbvio na primeira vez, e este texto ensina.
                   Os dois abrem a mesma folha — dois caminhos para a mesma
                   coisa é tolerância, não ambiguidade. -->
              <button class="t-ponto-check ${feito ? 'concluido' : ''}" onclick="${feito
                  ? `window._tConcluirPonto(${s.id}, 'pendente')`
                  : `window._tAbrirDesfecho(${s.id})`}">
                ${feito ? 'Reabrir' : 'Concluir'}
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
      ${pontosHtml || '<div class="t-vazio"><p>Nenhum atendimento nessa ficha ainda.</p></div>'}
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
  // O acompanhamento tem duas pernas: a PREVISAO de chegada, que o servidor
  // calcula sozinho e nunca falha, e a POSICAO no mapa, que depende do GPS
  // deste aparelho e so anda enquanto esta tela estiver aberta.
  //
  // A limitacao vale a pena repetir aqui, porque ela e a razao do desenho:
  // quando o tecnico sai para o Waze, o navegador CONGELA esta pagina e o
  // watchPosition para de disparar. Nao ha jeito de contornar isso em web —
  // nem instalado como aplicativo. Por isso a pagina do cliente sempre mostra
  // ha quanto tempo aquela posicao foi vista, em vez de fingir que e agora.
  async function criarLinkAcompanhamento(servicoId) {
    try {
      const r = await api(`/servicos/${servicoId}/rastreio`, { method: 'POST' });
      iniciarEnvioDePosicao(r.token);
      return `${location.origin}/acompanhar/${r.token}`;
    } catch (e) {
      // Sem o link a mensagem ainda vale. Avisar sem acompanhamento e melhor
      // do que nao avisar.
      console.warn('Nao consegui criar o link:', e.message);
      return null;
    }
  }

  // ===== ENVIO DA POSICAO =====
  let rastreioAtivo = null;   // { token, watchId, ultimoEnvio, wakeLock }

  const INTERVALO_ENVIO_MS = 20000;  // 20s: fluido no mapa sem torrar bateria
  const DISTANCIA_MINIMA_M = 40;     // parado no semaforo nao precisa reenviar

  // Leitura pior que isto NAO e posicao, e chute -- e vira "localizacao
  // aleatoria" na tela do cliente.
  //
  // O navegador so usa GPS de verdade quando ele tem sinal. Sem isso, ele
  // responde por Wi-Fi ou por IP, e um cliente que ve o tecnico a 8 km de
  // distancia perde a confianca no acompanhamento inteiro. Pior: no iPhone,
  // com "Localizacao Precisa" desligada, TODA leitura vem com erro de 1 a 3 km
  // e nada no aparelho avisa. 500m e o limite do que ainda ajuda alguem que
  // esta esperando na porta de casa.
  const PRECISAO_MAXIMA_M = 500;

  // ===== SELO DE GPS =====
  // A primeira versao disto falhava em SILENCIO: permissao negada era engolida
  // num catch vazio e ninguem no mundo ficava sabendo -- nem o tecnico, que
  // achava estar sendo acompanhado, nem o cliente, que via um mapa parado.
  // Este selo existe para que o estado do GPS seja sempre visivel na tela.
  function selo() {
    let el = document.getElementById('t-gps-selo');
    if (!el) {
      el = document.createElement('div');
      el.id = 't-gps-selo';
      el.className = 't-gps-selo';
      document.body.appendChild(el);
    }
    return el;
  }

  function mostrarGps(estado, texto) {
    const el = selo();
    if (!estado) { el.style.display = 'none'; return; }
    el.style.display = 'flex';
    el.className = `t-gps-selo ${estado}`;
    el.textContent = texto;
    // Bloqueado abre as instrucoes ao toque: mandar o tecnico "ir nas
    // configuracoes" sem dizer onde nao resolve o problema de ninguem.
    el.onclick = estado === 'bloqueado' ? explicarPermissao : null;
  }

  function explicarPermissao() {
    const ehIphone = /iphone|ipad|ipod/i.test(navigator.userAgent);
    alert(
      'O cliente nao consegue ver voce no mapa porque a localizacao esta '
      + 'bloqueada para este site.\n\nComo liberar:\n\n'
      + (ehIphone
          ? 'Ajustes > Safari > Localizacao > Perguntar ou Permitir.\n'
            + 'Depois feche e abra o app de novo.'
          : 'Toque no cadeado ao lado do endereco > Permissoes > Localizacao > '
            + 'Permitir.\nDepois recarregue a pagina.')
    );
  }

  function metrosEntre(a, b) {
    // Equirretangular em vez de haversine: em distancias de quarteirao o erro
    // e irrelevante e isso roda a cada leitura do GPS, no celular do tecnico.
    const R = 6371000, rad = Math.PI / 180;
    const x = (b.lng - a.lng) * rad * Math.cos((a.lat + b.lat) * rad / 2);
    const y = (b.lat - a.lat) * rad;
    return Math.sqrt(x * x + y * y) * R;
  }

  async function iniciarEnvioDePosicao(rastreioToken) {
    if (!navigator.geolocation) {
      mostrarGps('bloqueado', 'Este aparelho nao tem GPS');
      return;
    }
    pararEnvioDePosicao();  // nunca dois watch ao mesmo tempo

    rastreioAtivo = { token: rastreioToken, watchId: null, ultimo: null, ultimoEnvio: 0 };
    mostrarGps('procurando', 'Procurando sinal de GPS...');

    // Segura a tela acesa enquanto ele esta a caminho. Nao resolve o
    // congelamento ao trocar de app, mas cobre o caso real de quem deixa o
    // celular no suporte com o site aberto: sem isso a tela apaga em 30s e o
    // navegador comeca a estrangular o GPS.
    try {
      if ('wakeLock' in navigator) rastreioAtivo.wakeLock = await navigator.wakeLock.request('screen');
    } catch { /* negado ou sem suporte: segue sem, nao e essencial */ }

    rastreioAtivo.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        // Chegou leitura: a permissao existe, qualquer que fosse o palpite.
        gpsEstado = 'granted'; gpsErro = '';
        enviarPosicao(pos.coords);
      },
      (err) => {
        // Registra para o ping contar ao servidor. "Nao esta indo" precisa vir
        // com o motivo, senao o diagnostico volta a ser adivinhacao.
        gpsErro = `${err.code}:${(err.message || '').slice(0, 100)}`;
        if (err.code === err.PERMISSION_DENIED) {
          gpsEstado = 'denied';
          // Nao e "desliga quieto" como eu tinha feito: sem permissao o
          // acompanhamento simplesmente nao existe, e o tecnico precisa saber
          // disso ANTES de dizer ao cliente que ele esta sendo acompanhado.
          pararEnvioDePosicao();
          mostrarGps('bloqueado', 'Localizacao bloqueada — toque para liberar');
        } else {
          // Sem sinal (tunel, predio) nao e erro definitivo: o watch continua
          // tentando e volta sozinho quando o GPS pegar.
          mostrarGps('procurando', 'Sem sinal de GPS no momento');
        }
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 }
    );
  }

  async function enviarPosicao(coords) {
    if (!rastreioAtivo) return;

    const agora = Date.now();
    const ponto = { lat: coords.latitude, lng: coords.longitude };
    const precisao = Math.round(coords.accuracy || 0);

    // TRAVA DE QUALIDADE, antes de qualquer outra: nao mandar e melhor que
    // mandar errado. Posicao ruim nao e "melhor que nada" -- ela faz o cliente
    // ver o tecnico num bairro onde ele nao esta.
    if (precisao > PRECISAO_MAXIMA_M) {
      mostrarGps('procurando',
        `Localizacao imprecisa (${precisao} m) — nao enviada`);
      return;
    }

    // Duas travas juntas: nao envia antes do intervalo E nao envia se nao
    // andou. O GPS dispara varias vezes por segundo em movimento; sem isso
    // seriam centenas de requisicoes por corrida.
    const cedo = agora - rastreioAtivo.ultimoEnvio < INTERVALO_ENVIO_MS;
    const parado = rastreioAtivo.ultimo &&
                   metrosEntre(rastreioAtivo.ultimo, ponto) < DISTANCIA_MINIMA_M;
    if (cedo || parado) return;

    rastreioAtivo.ultimoEnvio = agora;
    rastreioAtivo.ultimo = ponto;

    try {
      const r = await api(`/rastreio/${rastreioAtivo.token}/posicao`, {
        method: 'POST',
        body: JSON.stringify({ ...ponto, precisao }),
      });
      // Desligar so quando o rastreio MORREU (ponto concluido, link expirado).
      // `gravado: false` sozinho nao serve: o servidor tambem recusa leitura
      // imprecisa, e desligar por causa disso mataria o acompanhamento na
      // primeira garagem ou tunel do trajeto.
      if (r && r.encerrado) { pararEnvioDePosicao(); return; }
      if (r && r.gravado === false) {
        mostrarGps('procurando', 'Localizacao imprecisa — aguardando GPS');
        return;
      }
      mostrarGps('enviando', `Cliente vendo voce no mapa (${precisao} m)`);
    } catch {
      // Sem rede agora, tenta na proxima leitura. Nao vira alerta -- quem esta
      // dirigindo nao pode receber pop-up -- mas o selo muda, porque o tecnico
      // precisa poder olhar de relance e saber que parou de chegar.
      mostrarGps('procurando', 'Sem conexao — vai retomar sozinho');
    }
  }

  function pararEnvioDePosicao() {
    if (!rastreioAtivo) return;
    if (rastreioAtivo.watchId != null) navigator.geolocation.clearWatch(rastreioAtivo.watchId);
    if (rastreioAtivo.wakeLock) { try { rastreioAtivo.wakeLock.release(); } catch {} }
    rastreioAtivo = null;
    mostrarGps(null);
  }

  // Retoma o envio ao ABRIR o app. Sem isto o rastreio era um evento de uma
  // vez so: morria com a pagina e o cliente ficava olhando mapa parado pelo
  // resto da viagem. Fechar o app, o celular matar a aba por memoria ou a tela
  // travar ja bastava -- e nao havia erro nenhum, so silencio.
  async function retomarRastreioAtivo() {
    try {
      const r = await api('/rastreios/ativos');
      const vivo = (r.rastreios || [])[0];
      if (vivo) iniciarEnvioDePosicao(vivo.token);
    } catch {
      // App abrindo sem sinal: nao ha o que retomar agora. A volta da conexao
      // dispara de novo (ver o listener de 'online' no fim do arquivo).
    }
  }

  // Voltou para o app depois do Waze? o wake lock cai sozinho quando a pagina
  // e escondida e NAO volta sozinho — sem isto, o resto da viagem ficaria com
  // a tela apagando de novo. Tambem forca um envio imediato, que e o momento
  // mais valioso: e a posicao mais nova desde que ele saiu da tela.
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState !== 'visible' || !rastreioAtivo) return;
    try {
      if ('wakeLock' in navigator && !rastreioAtivo.wakeLock) {
        rastreioAtivo.wakeLock = await navigator.wakeLock.request('screen');
      }
    } catch { /* segue sem */ }
    rastreioAtivo.ultimoEnvio = 0;
    rastreioAtivo.ultimo = null;
    navigator.geolocation.getCurrentPosition(
      (pos) => enviarPosicao(pos.coords), () => {}, { enableHighAccuracy: true });
  });

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
    if (!s) { toast('Atendimento não encontrado'); return; }

    // O rastreio comeca ANTES de montar a mensagem, porque o link dele entra
    // no texto. Se falhar, segue sem o link — avisar o cliente sem
    // acompanhamento e melhor que nao avisar. Mas quem manda precisa SABER
    // que faltou, senao o cliente recebe uma mensagem incompleta e ninguem
    // percebe (reclamado em 2026-09-03: "nao aparece o link").
    const linkAcompanhar = await criarLinkAcompanhamento(servicoId);
    if (!linkAcompanhar) {
      toast('Não consegui gerar o link de acompanhamento — a mensagem vai sem ele');
    }

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
    const lista = document.getElementById('lista-fichas');
    lista.style.display = '';
    // Reforça a animação de entrada mesmo se a classe já estivesse lá:
    // remove, força reflow (offsetWidth) e adiciona de novo — sem isso o
    // navegador acha que "nada mudou" e não toca a transição de novo.
    lista.classList.remove('t-tela-entrando');
    void lista.offsetWidth;
    lista.classList.add('t-tela-entrando');
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

  // ─── Desfecho do atendimento ──────────────────────────────────────
  //
  // "Concluído" sozinho não dizia nada: significava tanto "consertei" quanto
  // "fui lá e o cliente não estava". Desfechos opostos, ações opostas — e a
  // diferença ficava na cabeça de quem foi.
  //
  // Opção ESCOLHIDA em vez de campo de texto porque texto livre não soma nem
  // filtra: "troquei a placa" escrito de dez jeitos nunca vira relatório, e
  // "precisa de peça" digitado não dispara nada. Assim dá para responder
  // quantos atendimentos do mês pararam por falta de peça.
  //
  // Botão grande e pouco toque: o técnico está de pé, na calçada, com uma
  // mão segurando o celular e a outra ocupada.
  // Lista pedida pelo Kalebe em 2026-09-01 (sem "Resolvido") e "Resolvido"
  // voltou em 2026-09-02, a pedido dele de novo — ele tinha tirado de
  // propósito antes, mas quis de volta pra aparecer na aba Atendimentos.
  const DESFECHOS = [
    { tipo: 'resolvido',    rotulo: 'Resolvido',        sub: 'consertei na hora, nada pendente', icone: '✅' },
    { tipo: 'orcamento',    rotulo: 'Orçamento',        sub: 'dados + assinatura, escritório monta o valor', icone: '📋' },
    { tipo: 'precisa_peca', rotulo: 'Fazer Pedido de Peça', sub: 'diagnosticado, falta peça', icone: '🔧' },
    { tipo: 'volto_depois', rotulo: 'Reagendar Cliente', sub: 'preciso retornar',      icone: '↻' },
    { tipo: 'cotacao_peca', rotulo: 'Cotação de peça',  sub: 'não sei o preço ainda', icone: '💰' },
    { tipo: 'fazer_os',     rotulo: 'Fazer Ordem de Serviço', sub: 'dados + assinatura do cliente', icone: '📝' },
    { tipo: 'nao_atendido', rotulo: 'Cliente Ausente / Não foi possível atender', sub: 'não deu, precisa remarcar', icone: '!' },
  ];
  const MOTIVOS = ['Cliente ausente', 'Endereço errado', 'Cliente recusou',
                   'Aparelho sem defeito', 'Sem acesso ao local'];

  // Checklist obrigatório antes de fechar OS em campo (pedido de 2026-09-02,
  // especializado por tipo de aparelho em 2026-09-03 — a lista genérica não
  // cobria o que de fato importa checar em cada categoria antes de sair).
  //
  // Casamento por PALAVRA-CHAVE dentro de tipo_aparelho (campo livre, sem
  // enum fixo no banco) — "Geladeira Brastemp Frost Free" bate em
  // "geladeira" do mesmo jeito que "GELADEIRA" bate. A ORDEM importa: a
  // primeira chave que aparecer dentro do texto decide, por isso "ar
  // condicionado" vem antes de qualquer coisa que pudesse conter "ar" solto.
  const CHECKLIST_PADRAO = [
    'Testei o aparelho antes de sair',
    'Expliquei pro cliente o que foi feito',
    'Conferi a voltagem (127V — nunca arredondar pra 110V)',
  ];
  const CHECKLIST_POR_APARELHO = [
    { chaves: ['geladeira', 'refrigerador', 'freezer', 'frost free'], itens: [
      'Testei o compressor ligando e mantendo o ciclo',
      'Verifiquei vazamento de gás/água',
      'Conferi a vedação da borracha da porta',
      'Conferi a voltagem (127V — nunca arredondar pra 110V)',
      'Expliquei pro cliente o que foi feito',
    ]},
    { chaves: ['ar condicionado', 'ar-condicionado', 'split', 'climatizador'], itens: [
      'Testei o resfriamento por pelo menos 5 minutos',
      'Verifiquei vazamento de gás/água na unidade interna e externa',
      'Limpei o filtro',
      'Conferi a voltagem (127V — nunca arredondar pra 110V)',
      'Expliquei pro cliente o que foi feito',
    ]},
    { chaves: ['lava e seca', 'lavadora', 'máquina de lavar', 'maquina de lavar', 'tanquinho'], itens: [
      'Testei um ciclo completo de lavagem',
      'Verifiquei vazamento de água nas mangueiras',
      'Conferi a centrifugação',
      'Conferi a voltagem (127V — nunca arredondar pra 110V)',
      'Expliquei pro cliente o que foi feito',
    ]},
    { chaves: ['micro-ondas', 'microondas', 'micro ondas'], itens: [
      'Testei o aquecimento',
      'Conferi o giro do prato',
      'Conferi a voltagem (127V — nunca arredondar pra 110V)',
      'Expliquei pro cliente o que foi feito',
    ]},
    { chaves: ['lava-louça', 'lava louça', 'lava loucas'], itens: [
      'Testei um ciclo completo',
      'Verifiquei vazamento de água',
      'Conferi a voltagem (127V — nunca arredondar pra 110V)',
      'Expliquei pro cliente o que foi feito',
    ]},
    { chaves: ['fogão', 'fogao', 'cooktop'], itens: [
      'Testei todas as bocas',
      'Verifiquei vazamento de gás',
      'Conferi o acendimento automático',
      'Expliquei pro cliente o que foi feito',
    ]},
  ];
  function checklistParaAparelho(tipoAparelho) {
    const alvo = (tipoAparelho || '').toLowerCase();
    const grupo = CHECKLIST_POR_APARELHO.find(g => g.chaves.some(c => alvo.includes(c)));
    return grupo ? grupo.itens : CHECKLIST_PADRAO;
  }
  // Guarda o checklist que está de fato na tela agora — calculado uma vez ao
  // montar a folha (a partir do aparelho do atendimento) e reaproveitado ao
  // confirmar, pra nunca desalinhar item mostrado x item gravado.
  let _checklistAtual = CHECKLIST_PADRAO;

  // Ditado por voz (pedido de 2026-09-03: "mão suja de graxa, luva no
  // dedo — ditar em vez de digitar"). Web Speech API nativa do navegador,
  // sem custo nenhum de API — só existe de verdade no Chrome/Android hoje
  // (Safari/iOS não implementa), por isso o botão só aparece quando
  // `webkitSpeechRecognition` existe: não oferece o que não vai funcionar.
  const _SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;

  function _botaoDitado(idCampo) {
    if (!_SpeechRecognitionCtor) return '';
    return `<button type="button" class="t-df-ditado-btn" data-campo="${idCampo}"
              onclick="window._tAlternarDitado(this)" title="Ditar por voz">🎤 Ditar</button>`;
  }

  let _reconhecimentoAtivo = null;
  window._tAlternarDitado = function (botao) {
    if (_reconhecimentoAtivo) { _reconhecimentoAtivo.stop(); return; }

    const campo = document.getElementById(botao.dataset.campo);
    if (!campo) return;
    const rec = new _SpeechRecognitionCtor();
    rec.lang = 'pt-BR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    botao.classList.add('gravando');
    botao.textContent = '🔴 Ouvindo... (toque pra parar)';

    rec.onresult = (ev) => {
      const texto = ev.results[0][0].transcript;
      campo.value = campo.value ? `${campo.value} ${texto}` : texto;
      campo.dispatchEvent(new Event('input'));
    };
    rec.onerror = () => toast('Não consegui ouvir — tente de novo');
    rec.onend = () => {
      botao.classList.remove('gravando');
      botao.textContent = '🎤 Ditar';
      _reconhecimentoAtivo = null;
    };

    _reconhecimentoAtivo = rec;
    rec.start();
  };

  // ===== COMANDO DE VOZ (fecha a ficha sozinha, sem tocar na tela) =====
  // Pedido de 2026-09-03, corrigindo o que foi entregue antes: o "🎤 Ditar"
  // acima só TRANSCREVE pra dentro de um campo — o técnico ainda tinha que
  // escolher o tipo na tela e apertar Confirmar, o que não serve pra mão
  // suja de graxa/luva. Isto aqui ouve a frase inteira ("resolvido, motor
  // queimado"), reconhece o TIPO pela palavra-chave e fecha o atendimento
  // sozinho — sem nenhum toque a mais depois do toque que liga o microfone.
  //
  // Esse primeiro toque é inevitável: navegador nenhum deixa ligar o
  // microfone sem gesto direto do usuário (política de permissão, não
  // limitação nossa), e não existe "palavra de ativação" tipo "Hey Siri"
  // de graça em JS de navegador — só com um motor de wake-word dedicado,
  // que custa e teria que rodar sempre em segundo plano.
  //
  // Só RESOLVIDO, FAZER PEDIDO DE PEÇA e REAGENDAR fecham sozinhos: nenhum
  // dos três exige foto nem assinatura do cliente (ver window._tValidarConfirmar).
  // Os outros (orçamento, fazer OS, cotação, não atendido) sempre vão exigir
  // colher assinatura ou foto na tela — voz sozinha nunca vai bastar pra eles,
  // então o comando de voz só ADIANTA a escolha do tipo e abre a folha certa.
  const COMANDOS_VOZ = [
    { chaves: ['precisa de peça', 'precisa peça', 'falta a peça', 'falta peça', 'pedido de peça'], tipo: 'precisa_peca' },
    { chaves: ['reagendar', 'volto depois', 'vou voltar depois', 'remarcar'], tipo: 'volto_depois' },
    { chaves: ['cotação de peça', 'cotação', 'cotacao'], tipo: 'cotacao_peca' },
    { chaves: ['fazer ordem de serviço', 'fazer os', 'ordem de serviço'], tipo: 'fazer_os' },
    { chaves: ['orçamento', 'orcamento'], tipo: 'orcamento' },
    { chaves: ['não atendido', 'nao atendido', 'cliente ausente', 'não deu pra atender', 'não consegui atender'], tipo: 'nao_atendido' },
    // "resolvido" por último: é a chave mais curta e mais comum dentro de
    // outras frases ("resolvido depois que troquei a peça" também bate em
    // "peça"), então as mais específicas têm prioridade de checagem.
    { chaves: ['resolvido', 'resolvi', 'consertado', 'concertado'], tipo: 'resolvido' },
  ];
  const TIPOS_VOZ_FECHAM_SOZINHOS = new Set(['resolvido', 'precisa_peca', 'volto_depois']);

  function _botaoComandoVoz(servicoId) {
    if (!_SpeechRecognitionCtor) return '';
    return `<button type="button" class="t-ponto-link t-ponto-voz" data-servico="${servicoId}"
              onclick="window._tComandoVoz(${servicoId}, this)"
              title="Fale o que aconteceu, ex: 'resolvido, motor queimado' — fecha sozinho">
              🎤 Comando de voz</button>`;
  }

  let _reconhecimentoComandoAtivo = null;
  window._tComandoVoz = function (servicoId, botao) {
    if (_reconhecimentoComandoAtivo) { _reconhecimentoComandoAtivo.stop(); return; }

    const rec = new _SpeechRecognitionCtor();
    rec.lang = 'pt-BR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    const textoOriginal = botao.textContent;
    botao.classList.add('gravando');
    botao.textContent = '🔴 Ouvindo... fale o comando';

    rec.onresult = (ev) => {
      const transcript = (ev.results[0][0].transcript || '').trim();
      if (transcript) _tProcessarComandoVoz(servicoId, transcript);
    };
    rec.onerror = () => toast('Não consegui ouvir — tente de novo');
    rec.onend = () => {
      botao.classList.remove('gravando');
      botao.textContent = textoOriginal;
      _reconhecimentoComandoAtivo = null;
    };

    _reconhecimentoComandoAtivo = rec;
    rec.start();
  };

  function _tProcessarComandoVoz(servicoId, transcript) {
    const alvo = transcript.toLowerCase();
    let achado = null, resto = '';
    for (const c of COMANDOS_VOZ) {
      for (const chave of c.chaves) {
        const i = alvo.indexOf(chave);
        if (i === -1) continue;
        achado = c;
        // O que vem DEPOIS da palavra-chave vira observação/nome da peça —
        // "resolvido, motor queimado" → observação "motor queimado".
        resto = transcript.slice(i + chave.length).replace(/^[\s,.:;-]+/, '').trim();
        break;
      }
      if (achado) break;
    }

    if (!achado) {
      toast(`Não entendi um comando pra fechar sozinha ("${transcript}") — abrindo a ficha pra revisar`);
      window._tAbrirDesfecho(servicoId);
      const obs = document.getElementById('t-df-obs');
      if (obs) obs.value = transcript;
      return;
    }

    if (!TIPOS_VOZ_FECHAM_SOZINHOS.has(achado.tipo)) {
      const rotulo = DESFECHOS.find(d => d.tipo === achado.tipo)?.rotulo || achado.tipo;
      toast(`"${rotulo}" pede foto ou assinatura do cliente — completando na tela`);
      window._tAbrirDesfecho(servicoId);
      window._tEscolherDesfecho(achado.tipo);
      if (resto) {
        const obs = document.getElementById('t-df-obs');
        if (obs) obs.value = resto;
      }
      return;
    }

    const desfecho = { tipo: achado.tipo };
    if (achado.tipo === 'precisa_peca') desfecho.peca = resto || '';
    else if (resto) desfecho.observacao = resto;

    const rotulo = DESFECHOS.find(d => d.tipo === achado.tipo)?.rotulo || achado.tipo;
    toast(`Comando reconhecido: ${rotulo} — fechando sozinho…`, 'success');
    window._tConcluirPonto(servicoId, 'concluido', desfecho);
  }

  // Mesma lista de static/app.js e routes/ordens_servico.py:TIPOS_OS_ROTULO —
  // pedido de 2026-08-28: o técnico escolhe o termo jurídico da OS que ele
  // mesmo fecha em campo (ver "Fazer Ordem de Serviço" logo abaixo).
  const TIPOS_OS_ROTULO = {
    garantia_3_meses:              'Garantia 3 meses',
    entrada_oficina:                'OS de entrada na oficina',
    saida_oficina:                  'OS de saída da oficina',
    garantia_6_meses:               'OS garantia 6 meses',
    garantia_1_ano:                 'OS garantia 1 ano',
    retirada_pre_aprovada:          'OS de retirada pré-aprovada',
    vendas:                         'OS de vendas',
    retirada_aprovada:              'OS retirada aprovada',
    retirada_orcamento:             'OS de retirada para orçamento',
    acionamento_garantia_interno:   'Acionamento de garantia interno',
    acionamento_garantia_externo:   'Acionamento de garantia externo',
    avaliacao_tecnica:              'Avaliação técnica',
    cancelamento:                   'Cancelamento',
    pagamento_faturamento:          'Pagamento / Faturamento',
    higienizacao:                   'Higienização',
    retirado_aprovado:              'Retirado / Aprovado',
    criterio_orcamento_reparo:      'Critério de orçamento - reparo',
    criterios_condicoes_orcamento:  'Critérios e condições do orçamento',
  };

  function selo_desfecho(s) {
    const d = DESFECHOS.find(x => x.tipo === s.desfecho);
    if (!d) return '';
    const extra = s.desfecho_peca ? ' · ' + esc(s.desfecho_peca)
                : s.desfecho_motivo ? ' · ' + esc(s.desfecho_motivo) : '';
    return `<div class="t-desfecho-selo t-df-${s.desfecho}">${d.icone} ${d.rotulo}${extra}</div>${
      s.desfecho_obs ? `<div class="t-desfecho-obs">${esc(s.desfecho_obs)}</div>` : ''}`;
  }

  let _desfechoServicoId = null;
  let _desfechoTipo = null;
  let _desfechoFoto = null;
  // Desfecho "Orçamento" (pedido de 2026-09-02): o técnico pode já ter
  // combinado o valor com o cliente na hora ("feito no local") em vez de
  // sempre deixar pro escritório montar depois ("na base") — ver
  // window._tEscolherModoOrcamento.
  let _orcamentoModoLocal = false;

  // Reduz mantendo a imagem INTEIRA — sem recorte.
  //
  // O redutor de foto de perfil corta um quadrado central; numa etiqueta isso
  // decepa justamente o número de série, que é o dado pelo qual a peça é
  // pedida. Aqui a proporção é preservada e só o tamanho cai.
  //
  // 1280px no lado maior: é o que mantém legível um código impresso pequeno.
  // Abaixo disso a etiqueta começa a embaralhar no zoom, e o objetivo da foto
  // é justamente ser lida.
  //
  // Duas tentativas de decodificação porque o iPhone salva em HEIC por padrão
  // e a maioria dos navegadores não abre HEIC pela tag <img>: a imagem não
  // carrega e o erro morre calado.
  async function reduzirFoto(arquivo, ladoMaximo = 1280, qualidade = 0.72) {
    const desenhar = (fonte, largura, altura) => {
      const escala = Math.min(1, ladoMaximo / Math.max(largura, altura));
      const cv = document.createElement('canvas');
      cv.width = Math.round(largura * escala);
      cv.height = Math.round(altura * escala);
      const ctx = cv.getContext('2d');
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(fonte, 0, 0, cv.width, cv.height);
      return cv.toDataURL('image/jpeg', qualidade);
    };

    if (typeof createImageBitmap === 'function') {
      try {
        const bmp = await createImageBitmap(arquivo);
        const url = desenhar(bmp, bmp.width, bmp.height);
        bmp.close && bmp.close();
        return url;
      } catch { /* cai para o caminho 2 */ }
    }
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(arquivo);
      const img = new Image();
      img.onload = () => {
        try { resolve(desenhar(img, img.naturalWidth, img.naturalHeight)); }
        catch (e) { reject(new Error('Não consegui processar a foto: ' + e.message)); }
        finally { URL.revokeObjectURL(url); }
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        const nome = (arquivo.name || '').toLowerCase();
        reject(new Error(
          nome.endsWith('.heic') || nome.endsWith('.heif')
            ? 'Foto em HEIC (formato do iPhone). Ajustes > Câmera > Formatos > "Mais compatível". Ou envie um print da foto.'
            : 'Não consegui abrir essa foto.'));
      };
      img.src = url;
    });
  }

  window._tEscolherFoto = async function (input) {
    const arquivo = input.files && input.files[0];
    if (!arquivo) return;
    const previa = document.getElementById('t-df-previa');
    previa.innerHTML = '<span class="t-df-processando">preparando a foto...</span>';
    try {
      _desfechoFoto = await reduzirFoto(arquivo);
      previa.innerHTML = `
        <img class="t-df-thumb" src="${_desfechoFoto}" alt="Etiqueta do aparelho">
        <button type="button" class="t-df-remover-foto"
                onclick="window._tRemoverFoto()">remover</button>`;
    } catch (e) {
      _desfechoFoto = null;
      previa.innerHTML = `<span class="t-df-erro">${esc(e.message)}</span>`;
    } finally {
      input.value = '';   // permite escolher a MESMA foto de novo depois de remover
      window._tValidarConfirmar();
    }
  };

  window._tRemoverFoto = function () {
    _desfechoFoto = null;
    const previa = document.getElementById('t-df-previa');
    if (previa) previa.innerHTML = '';
    window._tValidarConfirmar();
  };

  // SOS (pedido de 2026-09-02) — endereço perigoso, acidente, imprevisto em
  // campo. Manda a posição atual se o navegador conseguir pegar rápido, mas
  // NÃO espera por ela — em emergência, esperar GPS é o oposto do que se quer.
  window._tPedirSos = function () {
    if (!confirm('Confirma pedido de ajuda ao escritório agora?')) return;
    const enviar = (lat, lng) => {
      api(`/${TOKEN}/sos`, { method: 'POST', body: JSON.stringify({ lat, lng }) })
        .then(() => toast('Escritório avisado. Aguarde contato.'))
        .catch(() => toast('Sem internet — tente de novo assim que possível.'));
    };
    if (navigator.geolocation) {
      const jaEnviou = { v: false };
      const disparar = (lat, lng) => { if (!jaEnviou.v) { jaEnviou.v = true; enviar(lat, lng); } };
      navigator.geolocation.getCurrentPosition(
        (pos) => disparar(pos.coords.latitude, pos.coords.longitude),
        () => disparar(null, null),
        { timeout: 3000 });
      setTimeout(() => disparar(null, null), 3200);
    } else {
      enviar(null, null);
    }
  };

  // Ler código de barras/QR pela câmera (pedido de 2026-09-02) — mesma ideia
  // do bipar de nota fiscal do painel, só que genérico pra qualquer campo.
  let _tScanCamera = null;

  // Máscara de telefone (pedido de 2026-09-02) — mesma lógica do painel.
  window._tFormatarTelefone = function (input) {
    let v = input.value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 10) v = `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7)}`;
    else if (v.length > 6) v = `(${v.slice(0, 2)}) ${v.slice(2, 6)}-${v.slice(6)}`;
    else if (v.length > 2) v = `(${v.slice(0, 2)}) ${v.slice(2)}`;
    input.value = v;
  };

  window._tTemCameraScan = function () {
    return ('BarcodeDetector' in window) && !!navigator.mediaDevices?.getUserMedia;
  };

  // A tela do técnico monta a interface toda via JS (não tem esse modal no
  // HTML estático) — cria uma vez, na primeira chamada, e reaproveita depois.
  function _tGarantirModalScan() {
    if (document.getElementById('t-modal-scan')) return;
    const div = document.createElement('div');
    div.id = 't-modal-scan';
    div.className = 't-modal-scan';
    div.innerHTML = `
      <div class="t-modal-scan-fundo" onclick="window._tFecharScanCodigo()"></div>
      <div class="t-modal-scan-painel">
        <p class="t-df-rotulo">Aponte a câmera pro código</p>
        <video id="t-scan-video" autoplay playsinline muted></video>
        <button type="button" class="t-df-limpar-assinatura" onclick="window._tFecharScanCodigo()">Cancelar</button>
      </div>`;
    document.body.appendChild(div);
  }

  window._tAbrirScanCodigo = async function (inputId) {
    _tGarantirModalScan();
    const modal = document.getElementById('t-modal-scan');
    if (!modal) return;
    modal.dataset.alvo = inputId;
    modal.classList.add('aberta');
    const video = document.getElementById('t-scan-video');
    try {
      const detector = new BarcodeDetector({ formats: ['code_128', 'code_39', 'ean_13', 'qr_code'] });
      _tScanCamera = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      video.srcObject = _tScanCamera;
      await video.play();
      const tick = async () => {
        if (!_tScanCamera) return;
        try {
          const cods = await detector.detect(video);
          if (cods.length) {
            const alvo = document.getElementById(modal.dataset.alvo);
            if (alvo) { alvo.value = cods[0].rawValue; alvo.dispatchEvent(new Event('input')); }
            window._tFecharScanCodigo();
            return;
          }
        } catch { /* frame ruim: tenta o próximo */ }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    } catch (e) {
      window._tFecharScanCodigo();
    }
  };

  window._tFecharScanCodigo = function () {
    if (_tScanCamera) { _tScanCamera.getTracks().forEach(t => t.stop()); _tScanCamera = null; }
    const video = document.getElementById('t-scan-video');
    if (video) video.srcObject = null;
    document.getElementById('t-modal-scan')?.classList.remove('aberta');
  };

  function blocoFoto(destaque, rotulo, ajuda) {
    rotulo = rotulo || 'Foto da etiqueta';
    const textoAjuda = ajuda !== undefined ? ajuda
      : (destaque ? 'É dela que sai o modelo e o número de série para pedir a peça.' : '');
    return `
      <label class="t-df-rotulo">${rotulo} ${destaque ? '' : '(opcional)'}</label>
      ${textoAjuda ? `<p class="t-df-ajuda">${textoAjuda}</p>` : ''}
      <label class="t-df-foto-botao">
        Tirar foto
        <input type="file" accept="image/*" capture="environment"
               onchange="window._tEscolherFoto(this)" hidden>
      </label>
      <div id="t-df-previa" class="t-df-previa"></div>`;
  }

  window._tAbrirDesfecho = function (servicoId) {
    _desfechoServicoId = servicoId;
    _desfechoTipo = null;
    _desfechoFoto = null;
    const folha = document.getElementById('t-folha-desfecho');
    if (!folha) return;
    folha.querySelector('.t-folha-corpo').innerHTML = `
      <div class="t-folha-titulo">O que aconteceu?</div>
      <div class="t-df-opcoes">
        ${DESFECHOS.map(d => `
          <button class="t-df-opcao" data-tipo="${d.tipo}"
                  onclick="window._tEscolherDesfecho('${d.tipo}')">
            <span class="t-df-icone">${d.icone}</span>
            <span class="t-df-txt"><b>${d.rotulo}</b><small>${d.sub}</small></span>
          </button>`).join('')}
      </div>
      <div id="t-df-extra"></div>
      <button class="t-df-confirmar" id="t-df-confirmar" disabled
              onclick="window._tConfirmarDesfecho()">Confirmar</button>`;
    folha.classList.add('aberta');
  };

  window._tFecharDesfecho = function () {
    document.getElementById('t-folha-desfecho')?.classList.remove('aberta');
    _desfechoServicoId = null;
  };

  window._tEscolherDesfecho = function (tipo) {
    _desfechoTipo = tipo;
    document.querySelectorAll('.t-df-opcao').forEach(b =>
      b.classList.toggle('ativa', b.dataset.tipo === tipo));

    const extra = document.getElementById('t-df-extra');
    if (tipo === 'precisa_peca') {
      extra.innerHTML = `
        <label class="t-df-rotulo" for="t-df-peca">Qual peça?</label>
        <input class="t-df-input" id="t-df-peca" autocomplete="off"
               placeholder="Código ou nome da peça">
        ${blocoFoto(true)}`;
      // Sem foco automático: abrir o teclado por cima da folha esconde o
      // botão de confirmar, e o técnico fica sem saber o que fazer.
    } else if (tipo === 'cotacao_peca') {
      // Código, nome E foto são obrigatórios aqui — sem os três a cotação
      // sai sem como identificar a peça de verdade (ver window._tValidarConfirmar).
      extra.innerHTML = `
        <label class="t-df-rotulo" for="t-df-codigo">Código da peça</label>
        <div class="t-campo-com-scan">
          <input class="t-df-input" id="t-df-codigo" autocomplete="off"
                 placeholder="Ex: DE97-01234A" oninput="window._tValidarConfirmar()">
          ${window._tTemCameraScan() ? `<button type="button" class="t-btn-scan-codigo" onclick="window._tAbrirScanCodigo('t-df-codigo')">📷</button>` : ''}
        </div>
        <label class="t-df-rotulo" for="t-df-nome-peca">Nome da peça</label>
        <input class="t-df-input" id="t-df-nome-peca" autocomplete="off"
               placeholder="Ex: Placa eletrônica" oninput="window._tValidarConfirmar()">
        ${blocoFoto(true)}`;
    } else if (tipo === 'nao_atendido') {
      extra.innerHTML = `
        <label class="t-df-rotulo">Por quê?</label>
        <div class="t-df-motivos">
          ${MOTIVOS.map(m => `
            <button class="t-df-motivo" data-motivo="${esc(m)}"
                    onclick="window._tEscolherMotivo(this)">${esc(m)}</button>`).join('')}
        </div>
        ${blocoFoto(true, 'Foto do comprovante', 'Comprova que você foi até o cliente — porta fechada, endereço, o que for.')}`;
    } else if (tipo === 'volto_depois') {
      extra.innerHTML = blocoFoto(false);
    } else if (tipo === 'fazer_os') {
      // Pedido de 2026-08-28: o técnico fecha o caso em campo — dados do
      // cliente, defeito, solução, forma de pagamento — e colhe a
      // assinatura na hora, sem depender do escritório abrir a OS depois.
      const s = (servicosAbertos || []).find(x => x.id === _desfechoServicoId) || {};
      _checklistAtual = checklistParaAparelho(s.tipo_aparelho);
      extra.innerHTML = `
        <label class="t-df-rotulo" for="t-df-fos-nome">Nome do cliente</label>
        <input class="t-df-input" id="t-df-fos-nome" value="${esc(s.cliente || '')}">
        <label class="t-df-rotulo" for="t-df-fos-telefone">Telefone</label>
        <input class="t-df-input" id="t-df-fos-telefone" value="${esc(s.telefone || '')}" oninput="window._tFormatarTelefone(this)">
        <div class="t-df-linha-dupla">
          <div><label class="t-df-rotulo" for="t-df-fos-aparelho">Aparelho</label>
            <input class="t-df-input" id="t-df-fos-aparelho" value="${esc(s.tipo_aparelho || '')}"></div>
          <div><label class="t-df-rotulo" for="t-df-fos-modelo">Modelo</label>
            <input class="t-df-input" id="t-df-fos-modelo" value="${esc(s.modelo || '')}"></div>
        </div>
        <label class="t-df-rotulo" for="t-df-fos-defeito">Defeito declarado</label>
        <textarea class="t-df-input" id="t-df-fos-defeito" rows="2">${esc(s.descricao || '')}</textarea>
        <label class="t-df-rotulo" for="t-df-fos-solucao">Nossa solução</label>
        <textarea class="t-df-input" id="t-df-fos-solucao" rows="3" placeholder="O que foi feito"></textarea>
        ${_botaoDitado('t-df-fos-solucao')}
        <label class="t-df-rotulo" for="t-df-fos-pagamento">Forma de pagamento</label>
        <select class="t-df-input" id="t-df-fos-pagamento">
          <option value="">Selecione...</option>
          <option value="Pix">Pix</option>
          <option value="Dinheiro">Dinheiro</option>
          <option value="Cartão">Cartão</option>
        </select>
        <label class="t-df-rotulo" for="t-df-fos-tipo-os">Tipo de OS / Termo (opcional)</label>
        <select class="t-df-input" id="t-df-fos-tipo-os">
          <option value="">Selecione...</option>
          ${Object.entries(TIPOS_OS_ROTULO).map(([v, r]) => `<option value="${v}">${esc(r)}</option>`).join('')}
        </select>
        ${blocoFoto(false)}
        <label class="t-df-rotulo">Checklist antes de fechar <span class="t-df-obrigatorio">*</span></label>
        <div class="t-df-checklist">
          ${_checklistAtual.map((item, i) => `
            <label class="t-df-checklist-item">
              <input type="checkbox" data-checklist="${i}" onchange="window._tValidarConfirmar()">
              ${esc(item)}
            </label>`).join('')}
        </div>
        <label class="t-df-rotulo">Assinatura do cliente <span class="t-df-obrigatorio">*</span></label>
        <p class="t-df-ajuda">Passe o celular pro cliente assinar aqui com o dedo.</p>
        <canvas id="t-assinatura-canvas" class="t-assinatura-canvas"></canvas>
        <button type="button" class="t-df-limpar-assinatura" onclick="window._tLimparAssinatura()">Limpar assinatura</button>`;
      // Chamada SÍNCRONA, não setTimeout(fn, 0) — pedido de 2026-08-28, achado
      // testando: setTimeout corre risco real de o cliente já ter começado a
      // assinar com o dedo antes do handler existir no canvas, capturando só
      // o fim do traço (assinatura "minúscula"/cortada, pior ainda em campo
      // com celular mais lento). getBoundingClientRect() força o reflow
      // pendente do innerHTML na hora — o canvas já sai com o tamanho certo.
      _tIniciarAssinatura();
    } else if (tipo === 'orcamento') {
      // Pedido de 2026-09-01: o técnico levanta o básico do cliente/aparelho
      // e colhe assinatura — quem monta o valor do orçamento (itens/preços)
      // é o escritório depois, por isso não pede solução nem forma de
      // pagamento aqui (ainda não existem, o orçamento nem foi feito).
      const s = (servicosAbertos || []).find(x => x.id === _desfechoServicoId) || {};
      _orcamentoModoLocal = false;
      extra.innerHTML = `
        <label class="t-df-rotulo">Onde vai ser feito o orçamento? <span class="t-df-obrigatorio">*</span></label>
        <div class="t-df-motivos">
          <button type="button" class="t-df-motivo ativa" data-modo="base"
                  onclick="window._tEscolherModoOrcamento(this)">Fazer orçamento na base</button>
          <button type="button" class="t-df-motivo" data-modo="local"
                  onclick="window._tEscolherModoOrcamento(this)">Orçamento feito no local</button>
        </div>
        <div id="t-df-orc-valor-bloco" style="display:none;">
          <label class="t-df-rotulo" for="t-df-orc-valor">Valor combinado com o cliente (R$)</label>
          <input class="t-df-input" type="number" step="0.01" min="0.01" inputmode="decimal"
                 id="t-df-orc-valor" oninput="window._tValidarConfirmar()">
          <p class="t-df-ajuda" id="t-df-orc-sugestao"></p>
          <label class="t-df-rotulo" for="t-df-orc-item">O que foi orçado</label>
          <input class="t-df-input" id="t-df-orc-item" placeholder="Ex: Troca do compressor">
        </div>
        <label class="t-df-rotulo" for="t-df-orc-nome">Nome do cliente</label>
        <input class="t-df-input" id="t-df-orc-nome" value="${esc(s.cliente || '')}">
        <label class="t-df-rotulo" for="t-df-orc-telefone">Telefone</label>
        <input class="t-df-input" id="t-df-orc-telefone" value="${esc(s.telefone || '')}" oninput="window._tFormatarTelefone(this)">
        <div class="t-df-linha-dupla">
          <div><label class="t-df-rotulo" for="t-df-orc-aparelho">Aparelho</label>
            <input class="t-df-input" id="t-df-orc-aparelho" value="${esc(s.tipo_aparelho || '')}"></div>
          <div><label class="t-df-rotulo" for="t-df-orc-modelo">Modelo</label>
            <input class="t-df-input" id="t-df-orc-modelo" value="${esc(s.modelo || '')}"></div>
        </div>
        <label class="t-df-rotulo" for="t-df-orc-defeito">Defeito declarado</label>
        <textarea class="t-df-input" id="t-df-orc-defeito" rows="2">${esc(s.descricao || '')}</textarea>
        ${blocoFoto(false)}
        <label class="t-df-rotulo">Assinatura do cliente <span class="t-df-obrigatorio">*</span></label>
        <p class="t-df-ajuda">Passe o celular pro cliente assinar aqui com o dedo.</p>
        <canvas id="t-assinatura-canvas" class="t-assinatura-canvas"></canvas>
        <button type="button" class="t-df-limpar-assinatura" onclick="window._tLimparAssinatura()">Limpar assinatura</button>`;
      // Mesmo motivo de fazer_os: chamada síncrona pra não perder o começo
      // do traço se o cliente já estiver com o dedo na tela.
      _tIniciarAssinatura();
    } else {
      extra.innerHTML = blocoFoto(false);
    }
    extra.insertAdjacentHTML('beforeend', `
      <label class="t-df-rotulo" for="t-df-obs">Observação</label>
      <textarea class="t-df-input t-df-obs" id="t-df-obs" rows="3"
                placeholder="Algo que a equipe precisa saber (opcional)"></textarea>
      ${_botaoDitado('t-df-obs')}`);
    window._tValidarConfirmar();
  };

  // ─── Assinatura do cliente: canvas simples, dedo ou mouse ───────────
  let _assinaturaCanvas = null, _assinaturaCtx = null, _assinaturaDesenhando = false;
  let _assinaturaTemTraco = false;

  function _tIniciarAssinatura() {
    const canvas = document.getElementById('t-assinatura-canvas');
    if (!canvas) return;
    const escala = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * escala;
    canvas.height = rect.height * escala;
    _assinaturaCanvas = canvas;
    _assinaturaCtx = canvas.getContext('2d');
    _assinaturaCtx.scale(escala, escala);
    _assinaturaCtx.strokeStyle = '#111';
    _assinaturaCtx.lineWidth = 2.2;
    _assinaturaCtx.lineCap = 'round';
    _assinaturaTemTraco = false;

    const posicao = (ev) => {
      const r = canvas.getBoundingClientRect();
      const t = ev.touches ? ev.touches[0] : ev;
      return { x: t.clientX - r.left, y: t.clientY - r.top };
    };
    const iniciarTraco = (ev) => {
      ev.preventDefault();
      _assinaturaDesenhando = true;
      const p = posicao(ev);
      _assinaturaCtx.beginPath();
      _assinaturaCtx.moveTo(p.x, p.y);
    };
    const desenharTraco = (ev) => {
      if (!_assinaturaDesenhando) return;
      ev.preventDefault();
      const p = posicao(ev);
      _assinaturaCtx.lineTo(p.x, p.y);
      _assinaturaCtx.stroke();
      _assinaturaTemTraco = true;
      window._tValidarConfirmar();
    };
    const pararTraco = () => { _assinaturaDesenhando = false; };

    canvas.onmousedown = iniciarTraco;
    canvas.onmousemove = desenharTraco;
    canvas.onmouseup = pararTraco;
    canvas.onmouseleave = pararTraco;
    canvas.ontouchstart = iniciarTraco;
    canvas.ontouchmove = desenharTraco;
    canvas.ontouchend = pararTraco;
  }

  window._tLimparAssinatura = function () {
    if (!_assinaturaCtx || !_assinaturaCanvas) return;
    _assinaturaCtx.clearRect(0, 0, _assinaturaCanvas.width, _assinaturaCanvas.height);
    _assinaturaTemTraco = false;
    window._tValidarConfirmar();
  };

  // Cotação de peça trava por código+nome+foto; Fazer OS e Orçamento travam
  // por nome do cliente + assinatura de verdade (sem isso não tem o que
  // documentar) — os outros desfechos continuam livres.
  window._tValidarConfirmar = function () {
    const btn = document.getElementById('t-df-confirmar');
    if (!btn) return;
    let ok = true;
    if (_desfechoTipo === 'cotacao_peca') {
      const codigo = document.getElementById('t-df-codigo')?.value.trim();
      const nome = document.getElementById('t-df-nome-peca')?.value.trim();
      ok = !!(codigo && nome && _desfechoFoto);
    } else if (_desfechoTipo === 'fazer_os') {
      const nome = document.getElementById('t-df-fos-nome')?.value.trim();
      const checks = document.querySelectorAll('[data-checklist]');
      const checklistOk = checks.length > 0 && Array.from(checks).every(c => c.checked);
      ok = !!(nome && _assinaturaTemTraco && checklistOk);
    } else if (_desfechoTipo === 'orcamento') {
      const nome = document.getElementById('t-df-orc-nome')?.value.trim();
      const valorLocal = Number(document.getElementById('t-df-orc-valor')?.value);
      ok = !!(nome && _assinaturaTemTraco && (!_orcamentoModoLocal || valorLocal > 0));
    } else if (_desfechoTipo === 'nao_atendido') {
      // Foto obrigatória — comprovante de que o técnico foi até o cliente.
      // Pedido de 2026-09-01, depois de reclamação sem comprovação.
      ok = !!_desfechoFoto;
    }
    btn.disabled = !ok;
  };

  window._tEscolherModoOrcamento = function (botao) {
    document.querySelectorAll('#t-df-extra .t-df-motivo').forEach(b => b.classList.toggle('ativa', b === botao));
    _orcamentoModoLocal = botao.dataset.modo === 'local';
    const bloco = document.getElementById('t-df-orc-valor-bloco');
    if (bloco) bloco.style.display = _orcamentoModoLocal ? '' : 'none';
    if (_orcamentoModoLocal) _tCarregarSugestaoPreco();
    window._tValidarConfirmar();
  };

  // Precificação inteligente (pedido de 2026-09-03) — média/mediana do que
  // JÁ foi aprovado pelo cliente pra esse mesmo tipo de aparelho, não
  // chute nem IA. Ver /relatorios/sugestao-preco no servidor.
  async function _tCarregarSugestaoPreco() {
    const alvo = document.getElementById('t-df-orc-sugestao');
    if (!alvo) return;
    const s = (servicosAbertos || []).find(x => x.id === _desfechoServicoId) || {};
    if (!s.tipo_aparelho) { alvo.textContent = ''; return; }
    try {
      const r = await api(`/relatorios/sugestao-preco?aparelho=${encodeURIComponent(s.tipo_aparelho)}`);
      alvo.textContent = r.n >= 3
        ? `💡 Histórico de ${r.n} orçamentos aprovados pra ${s.tipo_aparelho}: média R$ ${r.media.toFixed(2)} (de R$ ${r.minimo.toFixed(2)} a R$ ${r.maximo.toFixed(2)})`
        : '';
    } catch { alvo.textContent = ''; }
  }

  window._tEscolherMotivo = function (botao) {
    document.querySelectorAll('.t-df-motivo').forEach(b => b.classList.remove('ativa'));
    botao.classList.add('ativa');
  };

  window._tConfirmarDesfecho = function () {
    if (!_desfechoTipo || !_desfechoServicoId) return;
    const desfecho = { tipo: _desfechoTipo };
    if (_desfechoTipo === 'precisa_peca') {
      desfecho.peca = document.getElementById('t-df-peca')?.value.trim() || '';
    }
    if (_desfechoTipo === 'cotacao_peca') {
      desfecho.codigo = document.getElementById('t-df-codigo')?.value.trim() || '';
      desfecho.nome_peca = document.getElementById('t-df-nome-peca')?.value.trim() || '';
    }
    if (_desfechoTipo === 'nao_atendido') {
      desfecho.motivo = document.querySelector('.t-df-motivo.ativa')?.dataset.motivo || '';
    }
    if (_desfechoTipo === 'fazer_os') {
      desfecho.cliente_nome = document.getElementById('t-df-fos-nome')?.value.trim() || '';
      desfecho.cliente_telefone = document.getElementById('t-df-fos-telefone')?.value.trim() || '';
      desfecho.tipo_aparelho = document.getElementById('t-df-fos-aparelho')?.value.trim() || '';
      desfecho.modelo = document.getElementById('t-df-fos-modelo')?.value.trim() || '';
      desfecho.defeito_declarado = document.getElementById('t-df-fos-defeito')?.value.trim() || '';
      desfecho.solucao_os = document.getElementById('t-df-fos-solucao')?.value.trim() || '';
      desfecho.forma_pagamento = document.getElementById('t-df-fos-pagamento')?.value || '';
      desfecho.tipo_os = document.getElementById('t-df-fos-tipo-os')?.value || '';
      desfecho.checklist = JSON.stringify(_checklistAtual.map((item, i) => ({
        item, marcado: !!document.querySelector(`[data-checklist="${i}"]`)?.checked,
      })));
      if (_desfechoFoto) desfecho.foto_produto = _desfechoFoto;
      if (_assinaturaTemTraco && _assinaturaCanvas) {
        desfecho.assinatura = _assinaturaCanvas.toDataURL('image/png');
      }
    }
    if (_desfechoTipo === 'orcamento') {
      desfecho.orcamento_local = _orcamentoModoLocal;
      if (_orcamentoModoLocal) {
        desfecho.valor_local = Number(document.getElementById('t-df-orc-valor')?.value) || 0;
        desfecho.item_local = document.getElementById('t-df-orc-item')?.value.trim() || '';
      }
      desfecho.cliente_nome = document.getElementById('t-df-orc-nome')?.value.trim() || '';
      desfecho.cliente_telefone = document.getElementById('t-df-orc-telefone')?.value.trim() || '';
      desfecho.tipo_aparelho = document.getElementById('t-df-orc-aparelho')?.value.trim() || '';
      desfecho.modelo = document.getElementById('t-df-orc-modelo')?.value.trim() || '';
      desfecho.defeito_declarado = document.getElementById('t-df-orc-defeito')?.value.trim() || '';
      // Foto vai como foto_produto (na OS, igual Fazer OS) -- é o que ajuda o
      // escritório a montar o orçamento certo, não um registro solto do
      // atendimento.
      if (_desfechoFoto) desfecho.foto_produto = _desfechoFoto;
      if (_assinaturaTemTraco && _assinaturaCanvas) {
        desfecho.assinatura = _assinaturaCanvas.toDataURL('image/png');
      }
    }
    const obs = document.getElementById('t-df-obs')?.value.trim();
    if (obs) desfecho.observacao = obs;
    if (_desfechoFoto && _desfechoTipo !== 'fazer_os' && _desfechoTipo !== 'orcamento') desfecho.foto = _desfechoFoto;
    const id = _desfechoServicoId;
    window._tFecharDesfecho();
    window._tConcluirPonto(id, 'concluido', desfecho);
  };

  // Banner com link real (<a target="_blank">), não window.open() — abrir
  // aba programaticamente depois de um await costuma ser bloqueado pelo
  // navegador por não contar como gesto direto do usuário; um link de
  // verdade não tem esse problema.
  function _tMostrarEnvioCliente(link, telefoneDigitos) {
    const numero = telefoneDigitos && telefoneDigitos.length >= 10 ? `55${telefoneDigitos}` : '';
    const msg = encodeURIComponent(`Olá! Segue o documento da sua Ordem de Serviço da Porto Tec: ${link}`);
    const urlWhats = numero ? `https://wa.me/${numero}?text=${msg}` : `https://wa.me/?text=${msg}`;
    const banner = document.createElement('div');
    banner.className = 't-envio-cliente';
    banner.innerHTML = `
      <span>OS assinada ✓</span>
      <a href="${urlWhats}" target="_blank" rel="noopener" class="t-envio-cliente-btn">Enviar no WhatsApp</a>
      <button type="button" class="t-envio-cliente-fechar" onclick="this.parentElement.remove()">✕</button>`;
    document.body.appendChild(banner);
    setTimeout(() => banner.remove(), 30000);
  }

  window._tConcluirPonto = async function (servicoId, novoStatus, desfecho) {
    // O desfecho vai NA MESMA requisição do status: o app tem fila offline, e
    // duas requisições separadas poderiam subir só uma — deixando atendimento
    // concluído sem desfecho, ou desfecho de um atendimento que foi reaberto.
    const corpo = { status: novoStatus };
    if (desfecho) corpo.desfecho = desfecho;
    const opts = { method: 'PUT', body: JSON.stringify(corpo) };
    // Chegou: desliga o GPS na hora. O servidor tambem encerra o rastreio ao
    // concluir o ponto, mas esperar a proxima leitura responder "gravado:
    // false" gastaria bateria a toa depois de o trabalho ter acabado.
    if (novoStatus === 'concluido') pararEnvioDePosicao();

    try {
      const resp = await api(`/servicos/${servicoId}/status`, opts);
      toast(novoStatus === 'concluido' ? 'Atendimento marcado como feito' : 'Atendimento reaberto');
      // Fazer OS gerou um documento com link público — oferece mandar pro
      // cliente ali mesmo, sem passar pelo escritório (pedido de 2026-08-28).
      // Orçamento feito no local (2026-09-03): já nasce com preço combinado
      // e pronto pra aprovação (ver _status_orcamento no servidor) — mesma
      // lógica. Orçamento "pra base montar" fica de fora, ainda sem preço.
      const orcamentoProntoNaHora = desfecho?.tipo === 'orcamento' && desfecho.orcamento_local;
      if ((desfecho?.tipo === 'fazer_os' || orcamentoProntoNaHora) && resp?.desfecho?.token_cliente) {
        const link = `${location.origin}/os/cliente/${resp.desfecho.token_cliente}`;
        _tMostrarEnvioCliente(link, (desfecho.cliente_telefone || '').replace(/\D/g, ''));
      }
      if (fichaAbertaId) abrirFicha(fichaAbertaId);
      carregarFichas();
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
  let revisaoPendente = null;

  // O que este aparelho vai contar sobre si mesmo no ping de versao. Sem isto
  // nao ha como saber, do servidor, que versao o celular do tecnico roda nem se
  // a localizacao esta liberada -- e diagnosticar as cegas custou tres rodadas
  // de deploy em 2026-08-14.
  let gpsEstado = 'desconhecido';
  let gpsErro = '';

  // A Permissions API responde SEM pedir permissao nem acordar o GPS, entao da
  // para saber que esta negado antes de qualquer tentativa. Safari antigo nao
  // tem: nesse caso o estado so muda quando o watchPosition responde.
  (async function observarPermissao() {
    try {
      const st = await navigator.permissions.query({ name: 'geolocation' });
      gpsEstado = st.state;                       // granted | denied | prompt
      st.onchange = () => { gpsEstado = st.state; };
    } catch { /* sem Permissions API: fica 'desconhecido' ate o GPS responder */ }
  })();

  async function lerRevisao() {
    const q = new URLSearchParams({ app: VERSAO_TELA, gps: gpsEstado });
    if (gpsErro) q.set('gps_erro', gpsErro);
    const resp = await fetch(`${API}/versao?${q}`, { cache: 'no-store' });
    if (!resp.ok) throw new Error('revisão indisponível');
    const d = await resp.json();
    // O servidor diz qual versão do código ele serve. Se for outra, este app
    // está velho e precisa recarregar — ver conferirVersaoDoApp().
    conferirVersaoDoApp(d.app);
    return d.revisao;
  }

  // Recarrega a PÁGINA quando o código do servidor é mais novo que este.
  //
  // Por que isto existe: o técnico deixa o app aberto o dia inteiro. O service
  // worker é rede-primeiro para .js, mas isso só vale quando há um novo
  // carregamento de página — e não há. Em 2026-08-14 o Pedro tocou "A caminho"
  // quatro vezes seguidas rodando código de três versões atrás; o cliente não
  // via nada e ninguém tinha como perceber, porque o app parecia funcionar.
  //
  // A recarga espera a tela estar OCIOSA, mesma disciplina do auto-refresh do
  // painel: recarregar com um campo preenchido ou uma folha aberta jogaria
  // fora o que o técnico estava fazendo, e ele está no meio da rua.
  function conferirVersaoDoApp(versaoServidor) {
    if (!versaoServidor || versaoServidor === VERSAO_TELA) return;

    // Trava de UMA recarga por versão. Sem isto, se o JS servido continuar
    // desatualizado depois do reload (cache do navegador, deploy ainda
    // propagando), o app entra num laço de recarregar pra sempre — a tela
    // "piscando" que já aconteceu. Uma tentativa só; se não resolver, avisa
    // parado em vez de continuar tentando sozinho.
    if (sessionStorage.getItem('tRecarregouPara') === versaoServidor) {
      avisarVersaoTravada();
      return;
    }

    const ocupado = document.querySelector('.t-folha-fundo')
      || (document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName));
    if (ocupado) return;  // tenta de novo no próximo ciclo, daqui a 20s

    // Marca antes de recarregar: se algo der errado no reload, o selo na tela
    // continua mostrando a versão velha e o diagnóstico não mente.
    sessionStorage.setItem('tRecarregouPara', versaoServidor);
    toast('Atualizando o aplicativo...');
    setTimeout(() => location.reload(), 600);
  }

  function avisarVersaoTravada() {
    if (document.getElementById('t-aviso-versao')) return;
    const aviso = document.createElement('div');
    aviso.id = 't-aviso-versao';
    aviso.className = 't-aviso-versao';
    aviso.setAttribute('role', 'status');
    aviso.innerHTML = `
      <span>Nova versão disponível</span>
      <button type="button" onclick="location.reload()">Recarregar</button>`;
    document.body.appendChild(aviso);
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

    // NUNCA redesenha sozinho — só avisa. Antes recarregava a tela na hora
    // que a revisão mudava, e como QUALQUER escrita no site inteiro (o
    // Kalebe no painel, outro técnico, uma peça vinculada) bumpa essa mesma
    // revisão, num dia ativo isso disparava a cada 20-40s: exatamente o
    // "fica piscando" relatado em 2026-08-25 — só pra quem usa este app,
    // porque o painel (app.js) já tinha passado por essa mesma correção.
    // Redesenhar fica a cargo de quem toca "Atualizar" no aviso abaixo.
    revisaoPendente = revisao;
    mostrarAvisoDadosNovos();
  }

  // Aviso discreto, parado no canto — não redesenha nada sozinho, não rouba
  // foco, não some sozinho. Mesmo padrão do aviso de versão nova, mas pra
  // dado (rota/ficha), não pra código do app.
  function mostrarAvisoDadosNovos() {
    if (document.getElementById('t-aviso-dados')) return;
    const aviso = document.createElement('div');
    aviso.id = 't-aviso-dados';
    aviso.className = 't-aviso-versao';
    aviso.setAttribute('role', 'status');
    aviso.innerHTML = `
      <span>Rota atualizada disponível</span>
      <span style="display:flex;gap:8px;">
        <button type="button" id="t-aviso-dados-dispensar"
                style="background:transparent;color:#9aacc6;">Depois</button>
        <button type="button" id="t-aviso-dados-atualizar">Atualizar</button>
      </span>`;
    document.body.appendChild(aviso);

    document.getElementById('t-aviso-dados-atualizar').onclick = async () => {
      revisaoConhecida = revisaoPendente;
      aviso.remove();
      if (fichaAbertaId !== null) await abrirFicha(fichaAbertaId);
      else await carregarFichas();
      toast('Rota atualizada');
    };
    // Dispensar aceita a revisão sem redesenhar: quem dispensou não quer ser
    // perguntado de novo pelo mesmo lote de mudanças (mesma lógica do painel).
    document.getElementById('t-aviso-dados-dispensar').onclick = () => {
      revisaoConhecida = revisaoPendente;
      aviso.remove();
    };
  }

  // Selo de versão no rodapé. Sem ele não há como saber, olhando o celular do
  // técnico, se o código novo chegou ou se o service worker ainda está
  // servindo o antigo do cache — e sem essa resposta qualquer diagnóstico de
  // "não está indo" vira adivinhação. Subir junto com o CACHE_VERSAO do sw.js.
  const VERSAO_TELA = 'v204';

  (function marcarVersao() {
    const selo = document.createElement('div');
    selo.className = 't-selo-versao';
    selo.textContent = VERSAO_TELA;
    document.body.appendChild(selo);
  })();


  // ─── Ponto de almoço ────────────────────────────────────────────────
  //
  // Pedido de 2026-08-29: 1h contada a partir do "ir almoçar". O botão
  // reflete o estado de verdade (não um cronômetro local que reseta ao
  // fechar a aba) — por isso relê o servidor ao abrir a tela, e não confia
  // só em memória. Ficar vermelho depois de 60min é só visual pro próprio
  // técnico; quem controla o tempo de verdade é o painel do admin, que vê
  // desde quando cada um saiu.
  let almocoDesde = null;
  let almocoIntervalo = null;

  // "desde" vem cru do banco em UTC sem sufixo de fuso — new Date(string)
  // direto faz o navegador ler como horário LOCAL, e o contador saía até 3h
  // errado (pedido de 2026-09-02: "a data está vindo aleatória").
  function _parseDataBancoAlmoco(valor) {
    if (!valor) return null;
    let s = String(valor).trim().replace(' ', 'T');
    if (!/(Z|[+-]\d{2}:\d{2})$/.test(s)) s += 'Z';
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function _renderBotaoAlmoco() {
    const btn = document.getElementById('btn-almoco');
    if (!btn) return;
    if (!almocoDesde) {
      btn.textContent = '🍽 Ir almoçar';
      btn.className = 't-btn-almoco';
      return;
    }
    const inicio = _parseDataBancoAlmoco(almocoDesde);
    const minutos = inicio ? Math.max(0, Math.round((Date.now() - inicio.getTime()) / 60000)) : 0;
    const restante = 60 - minutos;
    const rotulo = restante >= 0 ? `faltam ${restante}min` : `${Math.abs(restante)}min atrasado`;
    btn.textContent = `⏱ Voltar do almoço (${rotulo})`;
    btn.className = 't-btn-almoco em-almoco' + (restante < 0 ? ' atrasado' : '');
  }

  async function carregarStatusAlmoco() {
    try {
      const r = await api('/almoco');
      almocoDesde = r.em_almoco ? r.desde : null;
    } catch { /* offline: mantém o que já tinha na tela */ }
    _renderBotaoAlmoco();
    clearInterval(almocoIntervalo);
    if (almocoDesde) almocoIntervalo = setInterval(_renderBotaoAlmoco, 30000);
  }

  window._tAlternarAlmoco = async function () {
    const btn = document.getElementById('btn-almoco');
    if (btn) btn.disabled = true;
    try {
      if (almocoDesde) {
        const r = await api('/almoco/voltar', { method: 'POST' });
        toast(`Volta do almoço registrada — ${r.duracao_min}min de almoço`);
      } else {
        await api('/almoco/iniciar', { method: 'POST' });
        toast('Almoço iniciado — bom apetite!');
      }
    } catch (e) {
      toast(e.message || 'Não consegui registrar. Tenta de novo.');
    } finally {
      if (btn) btn.disabled = false;
      carregarStatusAlmoco();
    }
  };

  carregarStatusAlmoco();

  carregarFichas().then(atualizarAvisoTopo);

  // Se o técnico já estava a caminho quando o app fechou, o envio volta aqui.
  retomarRastreioAtivo();

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
    // Voltou o sinal: se ele ainda está a caminho, o envio precisa retomar.
    // Sem isto, um túnel no começo da viagem desligaria o acompanhamento até
    // o fim dela.
    if (!rastreioAtivo) retomarRastreioAtivo();
  });
  window.addEventListener('offline', atualizarAvisoTopo);

  sincronizarFila();
})();
