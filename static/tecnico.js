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
  const DESFECHOS = [
    { tipo: 'resolvido',    rotulo: 'Resolvido',        sub: 'consertado na hora',    icone: '✓' },
    { tipo: 'precisa_peca', rotulo: 'Precisa de peça',  sub: 'diagnosticado, falta peça', icone: '🔧' },
    { tipo: 'volto_depois', rotulo: 'Volto depois',     sub: 'preciso retornar',      icone: '↻' },
    { tipo: 'nao_atendido', rotulo: 'Reagendar',        sub: 'não deu, precisa remarcar', icone: '!' },
  ];
  const MOTIVOS = ['Cliente ausente', 'Endereço errado', 'Cliente recusou',
                   'Aparelho sem defeito', 'Sem acesso ao local'];

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
    }
  };

  window._tRemoverFoto = function () {
    _desfechoFoto = null;
    const previa = document.getElementById('t-df-previa');
    if (previa) previa.innerHTML = '';
  };

  function blocoFoto(destaque) {
    return `
      <label class="t-df-rotulo">Foto da etiqueta ${destaque ? '' : '(opcional)'}</label>
      ${destaque ? '<p class="t-df-ajuda">É dela que sai o modelo e o número de série para pedir a peça.</p>' : ''}
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
    } else if (tipo === 'nao_atendido') {
      extra.innerHTML = `
        <label class="t-df-rotulo">Por quê?</label>
        <div class="t-df-motivos">
          ${MOTIVOS.map(m => `
            <button class="t-df-motivo" data-motivo="${esc(m)}"
                    onclick="window._tEscolherMotivo(this)">${esc(m)}</button>`).join('')}
        </div>
        ${blocoFoto(false)}`;
    } else {
      extra.innerHTML = blocoFoto(false);
    }
    extra.insertAdjacentHTML('beforeend', `
      <label class="t-df-rotulo" for="t-df-obs">Observação</label>
      <textarea class="t-df-input t-df-obs" id="t-df-obs" rows="3"
                placeholder="Algo que a equipe precisa saber (opcional)"></textarea>`);
    document.getElementById('t-df-confirmar').disabled = false;
  };

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
    if (_desfechoTipo === 'nao_atendido') {
      desfecho.motivo = document.querySelector('.t-df-motivo.ativa')?.dataset.motivo || '';
    }
    const obs = document.getElementById('t-df-obs')?.value.trim();
    if (obs) desfecho.observacao = obs;
    if (_desfechoFoto) desfecho.foto = _desfechoFoto;
    const id = _desfechoServicoId;
    window._tFecharDesfecho();
    window._tConcluirPonto(id, 'concluido', desfecho);
  };

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
      await api(`/servicos/${servicoId}/status`, opts);
      toast(novoStatus === 'concluido' ? 'Atendimento marcado como feito' : 'Atendimento reaberto');
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

    const ocupado = document.querySelector('.t-folha-fundo')
      || (document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName));
    if (ocupado) return;  // tenta de novo no próximo ciclo, daqui a 20s

    // Marca antes de recarregar: se algo der errado no reload, o selo na tela
    // continua mostrando a versão velha e o diagnóstico não mente.
    toast('Atualizando o aplicativo...');
    setTimeout(() => location.reload(), 600);
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
  const VERSAO_TELA = 'v55';

  (function marcarVersao() {
    const selo = document.createElement('div');
    selo.className = 't-selo-versao';
    selo.textContent = VERSAO_TELA;
    document.body.appendChild(selo);
  })();


  // ===== CHAT DA EQUIPE =====
  // O tecnico em campo nao tem conta: ele se identifica pelo TOKEN do proprio
  // link, igual ao resto do app dele. A sala e a mesma do painel, entao o que
  // o Kalebe escreve aparece aqui e vice-versa.
  const equipeVistos = new Set();   // trava contra mensagem duplicada
  let equipeOcupado = false;
  let equipeUltimoId = 0;
  let equipeAberto = false;
  let equipeNaoLidas = 0;

  function equipeMontar() {
    if (document.getElementById('t-chat-bolha')) return;

    const bolha = document.createElement('button');
    bolha.id = 't-chat-bolha';
    bolha.className = 't-chat-bolha';
    bolha.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg><span class="t-chat-badge" id="t-chat-badge"></span>`;
    document.body.appendChild(bolha);

    const janela = document.createElement('div');
    janela.id = 't-chat-janela';
    janela.className = 't-chat-janela';
    janela.innerHTML = `
      <div class="t-chat-topo">Equipe<small>Conversa interna — o cliente não vê</small></div>
      <div class="t-chat-corpo" id="t-chat-corpo"></div>
      <form class="t-chat-envio" id="t-chat-form">
        <input id="t-chat-texto" placeholder="Mensagem..." autocomplete="off" maxlength="1000">
        <button type="submit">↑</button>
      </form>`;
    document.body.appendChild(janela);

    bolha.addEventListener('click', () => {
      equipeAberto = !equipeAberto;
      janela.classList.toggle('aberto', equipeAberto);
      if (equipeAberto) {
        equipeNaoLidas = 0;
        document.getElementById('t-chat-badge').classList.remove('tem');
        document.getElementById('t-chat-corpo').scrollTop = 1e6;
      }
    });

    document.getElementById('t-chat-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const campo = document.getElementById('t-chat-texto');
      const texto = campo.value.trim();
      if (!texto) return;
      campo.value = '';
      try {
        await api('/equipe', { method: 'POST', body: JSON.stringify({ texto }) });
        equipeBuscar();
      } catch (err) {
        campo.value = texto;   // devolve: perder mensagem sem avisar e pior
        toast('Sem conexão — tente de novo');
      }
    });
  }

  async function equipeBuscar() {
    if (equipeOcupado) return;
    equipeOcupado = true;
    try {
      const d = await api(`/equipe?desde=${equipeUltimoId}`);
      const corpo = document.getElementById('t-chat-corpo');
      if (!corpo) return;
      (d.mensagens || []).forEach((m) => {
        if (equipeVistos.has(m.id)) return;
        equipeVistos.add(m.id);
        const minha = m.autor_nome === d.eu;
        const tipo = m.autor_tipo === 'sistema' ? 'sistema' : (minha ? 'minha' : 'deles');
        const nome = tipo === 'deles' ? `<b>${esc(m.autor_nome || '')}</b><br>` : '';
        corpo.insertAdjacentHTML('beforeend',
          `<div class="t-msg ${tipo}">${nome}${esc(m.texto)}</div>`);
        equipeUltimoId = Math.max(equipeUltimoId, m.id);
        if (!equipeAberto && !minha) equipeNaoLidas++;
      });
      if ((d.mensagens || []).length) corpo.scrollTop = corpo.scrollHeight;

      const badge = document.getElementById('t-chat-badge');
      if (badge) {
        badge.textContent = equipeNaoLidas;
        badge.classList.toggle('tem', equipeNaoLidas > 0);
      }
    } catch { /* sem sinal: proximo ciclo */ }
    finally { equipeOcupado = false; }
  }

  equipeMontar();
  equipeBuscar();
  setInterval(equipeBuscar, 15000);   // 15s: rede movel, mais espacado que o painel

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
