let fichaAtiva   = null;
let tecnicoAtivo = null;
let tecnicos     = [];

// ===== ÍCONES (SVG de linha, não emoji) =====
// Emoji como ícone de interface é o maior sinal visual de "feito às pressas
// por IA". Um único jogo de ícones consistente (estilo Feather: 24x24,
// stroke, sem preenchimento) resolve isso de vez — mesma linguagem visual
// em toda a tela, em vez de depender da fonte de emoji do sistema.
const ICONES = {
  chevron:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
  recolher:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/></svg>',
  mapa:       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>',
  pin:        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  usuario:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  ferramenta: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.42l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.94 7.94l-6.9 6.9a2.12 2.12 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.94-7.94z"/></svg>',
  estrela:    '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
  casa:       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  raio:       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  atualizar:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
  calendario: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
  clipboard:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>',
  check:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  x:          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
  minus:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  alerta:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  info:       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  externo:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
  plus:       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  editar:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/></svg>',
  concluir:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  historico:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  navegacao:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>',
  telefone:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
};

function icone(nome, cls = '') {
  const svg = ICONES[nome];
  if (!svg) return '';
  return svg.replace('<svg ', `<svg class="icone-svg${cls ? ' ' + cls : ''}" `);
}

const _ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/[&<>"']/g, c => _ESCAPES[c]);
}

function escCor(cor, fallback = '#4f8dfb') {
  return (typeof cor === 'string' && /^#[0-9a-fA-F]{6}$/.test(cor)) ? cor : fallback;
}

function fmtKm(v) {
  return (v === null || v === undefined || isNaN(v)) ? '—' : Number(v).toFixed(1);
}

function parseDataBanco(valor) {
  if (!valor) return null;
  let s = String(valor).trim().replace(' ', 'T');
  s = s.replace(/([+-]\d{2})$/, '$1:00');
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(s)) s += 'Z';
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

let mapaLeaflet  = null;
let mapaMarkers  = [];
let mapaPolyline = null;

function inicializarMapa(containerId) {
  if (mapaLeaflet) { mapaLeaflet.remove(); mapaLeaflet = null; }
  mapaMarkers = [];
  mapaPolyline = null;
  const el = document.getElementById(containerId);
  if (!el) return;
  mapaLeaflet = L.map(containerId, { zoomControl: true, attributionControl: false })
                 .setView([-23.55, -46.63], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 })
   .addTo(mapaLeaflet);
  L.control.attribution({ prefix: '© OSM' }).addTo(mapaLeaflet);
}

function renderizarMapaPontos(ficha, servicos, corTecnico = '#4f8dfb') {
  if (!mapaLeaflet) return;
  const cor = escCor(corTecnico);

  mapaMarkers.forEach(m => m.remove());
  mapaMarkers = [];
  if (mapaPolyline) { mapaPolyline.remove(); mapaPolyline = null; }

  const pontos = [];
  const temPartida = ficha.ponto_partida_lat != null && ficha.ponto_partida_lat !== 0;
  let atraso = 0; // escalona a queda dos marcadores em vez de tudo aparecer junto

  if (temPartida) {
    const lat = ficha.ponto_partida_lat, lng = ficha.ponto_partida_lng;
    pontos.push([lat, lng]);
    const icon = L.divIcon({
      className: '',
      html: `<div class="pin-anim" style="animation-delay:${atraso}ms;width:36px;height:36px;border-radius:50%;background:#fff8e0;border:2px solid #b87800;display:flex;align-items:center;justify-content:center;color:#b87800;box-shadow:0 2px 8px rgba(0,0,0,0.25);">${icone('estrela', 'icone-16')}</div>`,
      iconSize: [36, 36], iconAnchor: [18, 18],
    });
    mapaMarkers.push(
      L.marker([lat, lng], { icon }).addTo(mapaLeaflet)
       .bindPopup(`<b style="color:#b87800;display:flex;align-items:center;gap:5px;">${icone('casa', 'icone-14')} Partida</b><br><span style="font-size:12px;">${esc(ficha.ponto_partida)}</span>`)
    );
    atraso += 70;
  }

  const ordenados = [...servicos].sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999));

  ordenados.forEach((s, i) => {
    if (!s.lat || !s.lng || (s.lat === 0 && s.lng === 0)) return;
    pontos.push([s.lat, s.lng]);
    const num = i + 1;
    const icon = L.divIcon({
      className: '',
      html: `<div class="pin-anim" style="animation-delay:${atraso}ms;width:34px;height:34px;border-radius:50%;background:${cor};border:2px solid white;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-family:'JetBrains Mono',monospace;">${num}</div>`,
      iconSize: [34, 34], iconAnchor: [17, 17],
    });
    atraso += 70;
    const endLabel = s.numero
      ? `Nº ${esc(s.numero)} · ${esc(s.endereco_completo)}`
      : (esc(s.endereco_completo) || '—');

    const aparelhoPopup = [s.tipo_aparelho, s.modelo].filter(Boolean).join(' — ');

    mapaMarkers.push(
      L.marker([s.lat, s.lng], { icon }).addTo(mapaLeaflet).bindPopup(
        `<div style="min-width:180px;">
           <div style="font-weight:700;color:${cor};font-size:13px;margin-bottom:4px;display:flex;align-items:center;gap:5px;">${icone('pin', 'icone-13')} Parada ${num}</div>
           <div style="font-family:monospace;font-size:12px;color:#555;margin-bottom:2px;">${esc(formatCEP(s.cep))}</div>
           <div style="font-size:12px;color:#333;">${endLabel}</div>
           ${s.cliente ? `<div style="font-size:11px;color:#777;margin-top:4px;display:flex;align-items:center;gap:4px;">${icone('usuario', 'icone-11')} ${esc(s.cliente)}</div>` : ''}
           ${aparelhoPopup ? `<div style="font-size:11px;color:#777;display:flex;align-items:center;gap:4px;">${icone('ferramenta', 'icone-11')} ${esc(aparelhoPopup)}</div>` : ''}
           ${s.descricao ? `<div style="font-size:11px;color:#777;">${esc(s.descricao)}</div>` : ''}
         </div>`
      )
    );
  });

  if (pontos.length >= 2) {
    mapaPolyline = L.polyline(pontos, {
      color: cor, weight: 3, opacity: 0.85, dashArray: '6, 6',
    }).addTo(mapaLeaflet);
  }

  if (pontos.length === 1) mapaLeaflet.setView(pontos[0], 15);
  else if (pontos.length >= 2) mapaLeaflet.fitBounds(pontos, { padding: [32, 32] });

  setTimeout(() => {
    mapaLeaflet && mapaLeaflet.invalidateSize();
    animarTracadoRota();
  }, 120);
}

// Efeito de "traçar a rota": a linha nasce invisível e se revela até virar
// o tracejado de sempre — reforça visualmente que a rota acabou de ser calculada.
function animarTracadoRota() {
  if (!mapaPolyline) return;
  const path = mapaPolyline.getElement?.();
  if (!path || !path.getTotalLength) return;

  const comprimento = path.getTotalLength();
  path.style.transition = 'none';
  path.style.strokeDasharray = `${comprimento}`;
  path.style.strokeDashoffset = `${comprimento}`;
  path.getBoundingClientRect(); // força reflow antes de animar

  requestAnimationFrame(() => {
    path.style.transition = 'stroke-dashoffset 1.1s ease-out';
    path.style.strokeDashoffset = '0';
  });

  setTimeout(() => {
    if (!mapaPolyline) return;
    const p = mapaPolyline.getElement?.();
    if (p) { p.style.transition = 'none'; p.style.strokeDasharray = '6, 6'; p.style.strokeDashoffset = '0'; }
  }, 1180);
}

// Relógio vivo no cabeçalho, atualizado a cada segundo — reforça a
// sensação de painel operacional em tempo real, não uma tela estática.
function iniciarRelogio() {
  const el = document.getElementById('current-date');
  if (!el) return;

  function atualizar() {
    const agora = new Date();
    const dia = agora.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }).toUpperCase();
    const hora = agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.textContent = `${dia} · ${hora}`;
  }

  atualizar();
  setInterval(atualizar, 1000);
}

// Monitor de saúde real da API — o indicador do cabeçalho não é mais um
// ponto verde decorativo fixo: ele de fato bate no /api/health a cada
// 15s, mede o tempo de resposta e mostra offline se a chamada falhar.
async function verificarSaude() {
  const dot   = document.getElementById('status-dot');
  const texto = document.getElementById('status-texto');
  const lat   = document.getElementById('status-latencia');
  const pill  = document.getElementById('status-pill');
  if (!dot) return;

  const inicio = performance.now();
  try {
    const resp = await fetch(`${BASE}/api/health`, { cache: 'no-store' });
    const ms = Math.round(performance.now() - inicio);
    if (!resp.ok) throw new Error('unhealthy');

    dot.classList.remove('status-dot--erro');
    if (texto) texto.textContent = 'online';
    if (lat) lat.textContent = `${ms}ms`;
    if (pill) pill.title = `Sistema online · resposta em ${ms}ms`;
  } catch {
    dot.classList.add('status-dot--erro');
    if (texto) texto.textContent = 'offline';
    if (lat) lat.textContent = '';
    if (pill) pill.title = 'Sem conexão com o servidor';
  }
}

function iniciarMonitorSaude() {
  verificarSaude();
  setInterval(verificarSaude, 15000);
}

// ===== AUTO-REFRESH =====
// O servidor mantém um contador que sobe a cada escrita (ver bump_revisao no
// database.py). Aqui só perguntamos "o número mudou?" a cada 10s: a resposta
// tem duas dezenas de bytes, então perguntar é ordens de grandeza mais barato
// que rebaixar as fichas às cegas.
//
// O ponto delicado não é detectar a mudança — é escolher a HORA de aplicar.
// Recarregar por baixo de alguém que está digitando um endereço ou arrastando
// um ponto na rota destrói trabalho. Por isso a mudança detectada fica
// pendente e só entra quando a tela está ociosa.
const INTERVALO_REVISAO = 10000;

let _revisaoConhecida = null;
let _recarregandoAuto = false;

// Versão do código que ESTA página carregou. Subir junto com o CACHE_VERSAO
// do sw.js e o VERSAO_APP do extensions.py — os três contam a mesma história.
const VERSAO_PAINEL = 'v91';

// ─── Erros do navegador chegam ao servidor ──────────────────────────
// "O site fica dando erro" e impossivel de investigar do servidor: as rotas
// respondem 200 em 0,2s e o defeito mora na tela de outra pessoa. Com isto o
// erro real fica registrado e visivel em /api/erros-cliente.
let _ultimoErroEnviado = '';
let _ultimoEnvioErro = 0;

function reportarErro(origem, mensagem) {
  try {
    const texto = String(mensagem || '').slice(0, 500);
    const agora = Date.now();
    // Nao repete o mesmo erro nem manda mais de um a cada 5s: um erro dentro
    // de laco de render viraria centenas de requisicoes.
    if (texto === _ultimoErroEnviado && agora - _ultimoEnvioErro < 30000) return;
    if (agora - _ultimoEnvioErro < 5000) return;
    _ultimoErroEnviado = texto; _ultimoEnvioErro = agora;

    fetch('/api/erro-cliente', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origem, mensagem: texto,
                             versao: VERSAO_PAINEL, url: location.pathname }),
      keepalive: true,   // sobrevive se a pagina fechar logo depois
    }).catch(() => {});
  } catch { /* reportar erro nao pode gerar erro */ }
}

window.addEventListener('error', (e) => {
  reportarErro('window.onerror',
    `${e.message} @ ${(e.filename || '').split('/').pop()}:${e.lineno}`);
});
window.addEventListener('unhandledrejection', (e) => {
  reportarErro('promise', String(e.reason && e.reason.message || e.reason));
});

async function _lerRevisao() {
  const resp = await fetch(`${BASE}/api/versao`, { cache: 'no-store' });
  if (!resp.ok) throw new Error('revisão indisponível');
  const dados = await resp.json();
  _conferirVersaoDoPainel(dados.app);
  if (typeof pintarBadgeChat === 'function') pintarBadgeChat(dados.chat_nao_lidas);
  return dados.revisao;
}

// Recarrega a página quando o servidor já serve código mais novo.
//
// O painel fica aberto o dia inteiro; sem isto, correção nenhuma chega até
// alguém lembrar de apertar F5. Foi o que aconteceu com a subida de foto: o
// código novo estava no ar e a tela do Kalebe rodava o antigo.
//
// Só recarrega com a tela OCIOSA — mesma disciplina do auto-refresh: jogar
// fora um formulário meio preenchido seria pior que esperar o próximo ciclo.
function _conferirVersaoDoPainel(versaoServidor) {
  if (!versaoServidor || versaoServidor === VERSAO_PAINEL) return;
  if (document.getElementById('aviso-versao')) return;

  // Também deixou de recarregar sozinho. Recarga de página é ainda mais
  // violenta que redesenhar uma aba — leva junto rolagem, ficha aberta e
  // qualquer coisa em andamento. O aviso fica parado até alguém escolher.
  const aviso = document.createElement('div');
  aviso.id = 'aviso-versao';
  aviso.className = 'aviso-atualizacao aviso-versao';
  aviso.setAttribute('role', 'status');
  aviso.innerHTML = `
    <span class="aviso-ponto" aria-hidden="true"></span>
    <span class="aviso-texto">Nova versão do sistema</span>
    <button type="button" class="aviso-btn" id="aviso-versao-btn">Recarregar</button>`;
  document.body.appendChild(aviso);
  document.getElementById('aviso-versao-btn').onclick = () => location.reload();
}

// Chamado depois das escrituras do próprio usuário: a tela dele já se
// atualizou sozinha na resposta da ação, então absorvemos o novo número sem
// disparar recarga. Sem isso, todo clique em "salvar" provocaria um segundo
// recarregamento redundante 10s depois.
async function sincronizarRevisaoSilenciosa() {
  try { _revisaoConhecida = await _lerRevisao(); } catch { /* silencioso de propósito */ }
}

function _telaOciosa() {
  const ativo = document.activeElement;
  if (ativo && ['INPUT', 'TEXTAREA', 'SELECT'].includes(ativo.tagName)) return false;
  if (document.querySelector('.modal-overlay.open')) return false;
  // Classes que o SortableJS aplica enquanto o arraste está em curso
  if (document.querySelector('.sortable-chosen, .sortable-drag')) return false;
  return true;
}

async function recarregarViewAtual() {
  if (_recarregandoAuto) return;
  _recarregandoAuto = true;

  try {
    const abas = ['roteiros', 'cep', 'historico', 'pecas'];
    const ativa = abas.find(t => document.getElementById(`mtab-${t}`)?.classList.contains('active')) || 'roteiros';

    if (ativa === 'roteiros') {
      await carregarTecnicos();
      // A ficha aberta é redesenhada depois da sidebar porque carregarTecnicos
      // reconstrói a lista inteira e o detalhe precisa refletir o estado novo.
      if (fichaAtiva) await renderFichaDetalhe(fichaAtiva);
    } else if (ativa === 'historico') {
      await carregarHistorico();
    } else if (ativa === 'pecas') {
      await carregarPecas();
    }
    // A aba "cep" não mostra dado compartilhado — é uma consulta pontual do
    // usuário e recarregar apagaria o resultado que ele está lendo.

    carregarSeloPecas(); // o selo vermelho aparece em qualquer aba
  } finally {
    _recarregandoAuto = false;
  }
}

async function verificarRevisao() {
  if (document.hidden) return; // aba em segundo plano não precisa gastar rede

  let revisao;
  try {
    revisao = await _lerRevisao();
  } catch {
    return; // offline ou servidor caído: o monitor de saúde já avisa isso
  }

  if (_revisaoConhecida === null) {
    _revisaoConhecida = revisao; // primeira leitura só estabelece a referência
    return;
  }
  if (revisao === _revisaoConhecida) return;

  // NUNCA redesenha sozinho. Só avisa.
  //
  // Antes, detectada a mudança, a tela era redesenhada na hora — protegida
  // apenas por _telaOciosa(), que considera "ocupado" campo focado, modal
  // aberto ou arraste. Ler uma ficha, comparar dois endereços ou rolar uma
  // lista longa não conta como nenhum dos três: para o código a tela estava
  // ociosa, e o trabalho de quem estava lendo era jogado fora de 10 em 10
  // segundos. O Kalebe descreveu como "resetando o que eu estou fazendo",
  // que é exatamente o que era.
  //
  // A troca: detectar continua automático (custa dezenas de bytes), APLICAR
  // passa a ser decisão de quem está na frente da tela. Ninguém perde
  // contexto sem ter pedido.
  _revisaoPendente = revisao;
  mostrarAvisoAtualizacao();
}

// ─── Aviso de dados novos (não invasivo) ────────────────────────────
// Fica parado num canto até alguém clicar. Não rouba foco, não fecha
// sozinho, não desloca o conteúdo da página.
let _revisaoPendente = null;

function mostrarAvisoAtualizacao() {
  let aviso = document.getElementById('aviso-atualizacao');
  if (aviso) return;   // já está na tela; não empilha nem repinta

  aviso = document.createElement('div');
  aviso.id = 'aviso-atualizacao';
  aviso.className = 'aviso-atualizacao';
  aviso.setAttribute('role', 'status');
  aviso.innerHTML = `
    <span class="aviso-ponto" aria-hidden="true"></span>
    <span class="aviso-texto">Há dados novos</span>
    <button type="button" class="aviso-btn" id="aviso-atualizar-btn">Atualizar</button>
    <button type="button" class="aviso-fechar" id="aviso-dispensar-btn"
            title="Dispensar" aria-label="Dispensar">&times;</button>`;
  document.body.appendChild(aviso);

  document.getElementById('aviso-atualizar-btn').onclick = async () => {
    _revisaoConhecida = _revisaoPendente;
    aviso.remove();
    await recarregarViewAtual();
  };
  // Dispensar aceita a revisão sem redesenhar: quem dispensou não quer ser
  // perguntado de novo pelo mesmo lote de mudanças.
  document.getElementById('aviso-dispensar-btn').onclick = () => {
    _revisaoConhecida = _revisaoPendente;
    aviso.remove();
  };
}

function iniciarAutoRefresh() {
  sincronizarRevisaoSilenciosa();
  setInterval(verificarRevisao, INTERVALO_REVISAO);

  // Voltar para a aba é o momento de maior chance de estar desatualizado —
  // esperar o próximo ciclo de 10s aqui seria exatamente o "ter que recarregar
  // a página" que este mecanismo existe para eliminar.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) verificarRevisao();
  });
  window.addEventListener('online', verificarRevisao);
}

document.addEventListener('DOMContentLoaded', () => {
  iniciarRelogio();
  iniciarMonitorSaude();
  iniciarAutoRefresh();
  iniciarFiltroHistorico();
  carregarUsuarioLogado();
  iniciarChatPainel();
  carregarTecnicos();
  _vcepRenderHistorico();
  carregarSeloPecas();
  carregarSeloAgendar();
  carregarSetores();
});

// Registro do PWA — silencioso, não bloqueia nada se falhar (ex: em http
// local sem TLS, service worker é recusado pelo navegador por design).
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js').catch((e) => {
      console.warn('Service worker não registrado:', e.message);
    });
  });
}

// ===== ABAS PRINCIPAIS (Roteiros / Verificar CEP) =====
// Texto virando ARGUMENTO de onclick dentro de atributo HTML.
//
// JSON.stringify devolve a string entre aspas DUPLAS, e o atributo onclick
// também usa aspas duplas: o atributo terminava no meio do nome e o
// navegador reclamava "Unexpected end of input" — o modal não abria e o
// erro morria no console. Escapar as aspas para entidade resolve, porque o
// navegador desfaz a entidade antes de interpretar o JavaScript.
const argJs = (v) => JSON.stringify(String(v ?? '')).replace(/"/g, '&quot;');

function switchMainTab(tab) {
  const isRoteiros  = tab === 'roteiros';
  const isCep       = tab === 'cep';
  const isHistorico = tab === 'historico';
  const isPecas     = tab === 'pecas';
  const isDiag      = tab === 'diagnostico';
  const isAtend     = tab === 'atendimentos';
  const isEstoque   = tab === 'estoque';
  const isOS        = tab === 'os';
  const isAgendar   = tab === 'agendar';

  document.getElementById('panel-roteiros-sidebar').style.display = isRoteiros ? 'flex' : 'none';
  document.getElementById('panel-roteiros-main').style.display = isRoteiros ? 'block' : 'none';
  document.getElementById('panel-cep').style.display = isCep ? 'block' : 'none';
  document.getElementById('panel-historico').style.display = isHistorico ? 'block' : 'none';
  document.getElementById('panel-pecas').style.display = isPecas ? 'block' : 'none';
  document.getElementById('panel-diagnostico').style.display = isDiag ? 'block' : 'none';
  document.getElementById('panel-atendimentos').style.display = isAtend ? 'block' : 'none';
  document.getElementById('panel-estoque').style.display = isEstoque ? 'block' : 'none';
  document.getElementById('panel-os').style.display = isOS ? 'block' : 'none';
  document.getElementById('panel-agendar').style.display = isAgendar ? 'block' : 'none';

  document.getElementById('mtab-roteiros').classList.toggle('active', isRoteiros);
  document.getElementById('mtab-cep').classList.toggle('active', isCep);
  document.getElementById('mtab-historico').classList.toggle('active', isHistorico);
  document.getElementById('mtab-pecas').classList.toggle('active', isPecas);
  document.getElementById('mtab-diagnostico').classList.toggle('active', isDiag);
  document.getElementById('mtab-atendimentos').classList.toggle('active', isAtend);
  document.getElementById('mtab-estoque').classList.toggle('active', isEstoque);
  document.getElementById('mtab-os').classList.toggle('active', isOS);
  document.getElementById('mtab-agendar').classList.toggle('active', isAgendar);

  // Foco automático no campo de CEP ao abrir a aba, pra já poder digitar
  if (isCep) {
    setTimeout(() => document.getElementById('verificar-cep-input')?.focus(), 80);
  }
  if (isHistorico) {
    carregarHistorico();
    carregarComparativoTecnicos();
  }
  if (isDiag) {
    carregarDiagnostico();
  }
  if (isPecas) {
    carregarPecas();
  }
  if (isAtend) {
    carregarDesfechos();
  }
  if (isEstoque) {
    abrirEstoqueRaiz();
  }
  if (isOS) {
    carregarOS();
  }
  if (isAgendar) {
    carregarAgendarClientes();
  }
}

const BASE = '';
const TIMEOUT_PADRAO = 45000;

async function api(path, options = {}, timeoutMs = TIMEOUT_PADRAO) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const res = await fetch(BASE + '/api' + path, {
      headers: { 'Content-Type': 'application/json' },
      signal: ctrl.signal,
      ...options,
    });

    const texto = await res.text();
    let data = {};
    if (texto) {
      try { data = JSON.parse(texto); }
      catch { throw new Error(`Resposta inválida do servidor (HTTP ${res.status}).`); }
    }

    // Sessao caida tem tratamento PROPRIO, e nao vira "erro ao carregar".
    //
    // Sem isto, perder a sessao fazia TODA tela mostrar "nao foi possivel
    // carregar" -- o "site dando erro toda hora" que o Kalebe relatou em
    // 2026-08-17. O usuario nao tem como adivinhar que precisa logar de novo.
    if (res.status === 401) {
      reportarErro('sessao-expirada', `401 em ${path}`);
      location.href = '/login?next=' + encodeURIComponent(location.pathname);
      throw new Error('Sessão expirada — abrindo a tela de login');
    }

    if (!res.ok) throw new Error(data.erro || `Erro ${res.status}`);

    // Escrita do próprio usuário: a tela dele já reflete o resultado, então
    // absorvemos a revisão nova em silêncio. Sem isso o auto-refresh veria o
    // contador subir e recarregaria tudo de novo logo depois de cada ação.
    const metodo = (options.method || 'GET').toUpperCase();
    if (metodo !== 'GET' && typeof sincronizarRevisaoSilenciosa === 'function') {
      sincronizarRevisaoSilenciosa(); // sem await — não atrasa a resposta ao usuário
    }

    return data;

  } catch (e) {
    if (e.name === 'AbortError') {
      throw new Error('O servidor demorou demais para responder. Tente de novo.');
    }
    if (e instanceof TypeError) {
      throw new Error('Sem conexão com o servidor.');
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

// ─── Setores (Panasonic / Philco / Loja / ...) ──────────────────────
// Setor fica no PONTO, não na ficha: uma rota do dia pode ter uma geladeira
// Panasonic e uma lavadora Philco, e só separando no ponto dá pra contabilizar
// cada frente direito.
let setores = [];

async function carregarSetores() {
  try {
    const r = await api('/setores');
    setores = r.setores || [];
  } catch (e) {
    setores = [];
    console.warn('setores não carregados:', e.message);
  }
  return setores;
}

// Lembra o último setor usado. A maioria dos dias é de uma frente só, então
// pré-selecionar acerta quase sempre e transforma o campo obrigatório em zero
// cliques a mais. Fica no localStorage por ser preferência de quem está na
// máquina, não dado do negócio — não vale uma coluna no banco.
const CHAVE_ULTIMO_SETOR = 'portotec:ultimo-setor';

function ultimoSetorUsado() {
  const id = localStorage.getItem(CHAVE_ULTIMO_SETOR);
  // Só serve se o setor ainda existir e estiver ativo: setor desativado no
  // meio do caminho deixaria o formulário abrir com uma opção inválida.
  return setorPorId(id) ? id : null;
}

function lembrarSetor(id) {
  if (id) localStorage.setItem(CHAVE_ULTIMO_SETOR, String(id));
}

// Data de hoje como "AAAA-MM-DD" no fuso LOCAL. O toISOString devolveria UTC
// e, das 21h em diante no Brasil, marcaria a ficha do dia seguinte como hoje.
function dataDeHoje() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

function preencherSelectSetor(idSelect, selecionado = null) {
  const sel = document.getElementById(idSelect);
  if (!sel) return;

  // Sem escolha explícita, cai no último usado. O placeholder é "Selecione..."
  // e não "Sem setor" porque sem setor deixou de ser uma opção válida: 84% dos
  // pontos estavam assim e o relatório por setor não valia nada.
  const alvo = selecionado ?? ultimoSetorUsado();

  sel.innerHTML = `<option value="">Selecione o setor...</option>` +
    setores.map(s => `
      <option value="${s.id}" ${String(s.id) === String(alvo) ? 'selected' : ''}>
        ${esc(s.nome)}
      </option>`).join('');
}

function setorPorId(id) {
  return setores.find(s => String(s.id) === String(id)) || null;
}

// ─── Classificação em lote dos pontos órfãos ────────────────────────
// Tornar o setor obrigatório resolve daqui pra frente. Não conserta os 32
// pontos que já entraram sem classificação — e mandar o usuário abrir ponto
// por ponto seria repetir o atrito que criou o problema.
async function abrirClassificacaoEmLote() {
  const modal = document.getElementById('modal-classificar');
  const corpo = document.getElementById('classificar-corpo');
  const btn   = document.getElementById('btn-aplicar-lote');

  modal.classList.add('open');
  corpo.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:20px;"><div class="spinner"></div> Procurando atendimentos sem setor...</div>`;
  preencherSelectSetor('lote-setor');

  let r;
  try {
    r = await api('/servicos/sem-setor');
  } catch (e) {
    corpo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const servicos = r.servicos || [];
  if (servicos.length === 0) {
    corpo.innerHTML = `<div style="padding:18px;text-align:center;color:var(--text-muted);font-size:12px;">Nenhum atendimento sem setor. Tudo classificado.</div>`;
    btn.style.display = 'none';
    return;
  }

  // Agrupa por ficha: a decisão real é "esta rota inteira é Panasonic", quase
  // nunca ponto a ponto. Ver os pontos juntos por dia é o que torna a escolha
  // rápida em vez de uma lista solta de 32 nomes.
  const porFicha = new Map();
  servicos.forEach(s => {
    if (!porFicha.has(s.ficha_id)) porFicha.set(s.ficha_id, []);
    porFicha.get(s.ficha_id).push(s);
  });

  corpo.innerHTML = [...porFicha.entries()].map(([fichaId, pontos]) => `
    <div class="conc-titulo" style="display:flex;align-items:center;gap:8px;">
      <span class="vg-tecnico-dot" style="background:${escCor(pontos[0].tecnico_cor)}"></span>
      ${esc(pontos[0].dia_semana)} · ${esc(pontos[0].tecnico_nome || 'sem técnico')}
      <button type="button" class="btn btn-ghost btn-sm" style="margin-left:auto;"
              onclick="marcarPontosDaFicha(${fichaId})">Marcar a rota toda</button>
    </div>
    ${pontos.map(p => `
      <label class="conc-item" style="cursor:pointer;align-items:center;">
        <input type="checkbox" class="lote-check" data-ficha="${fichaId}" value="${p.id}">
        <div style="flex:1;min-width:0;">
          <div class="conc-cliente">${esc(p.cliente) || 'Cliente sem nome'}</div>
          <div class="conc-meta">${esc(p.tipo_aparelho) || '—'}${p.modelo ? ' · ' + esc(p.modelo) : ''}${p.numero_os ? ' · OS ' + esc(p.numero_os) : ''}</div>
        </div>
      </label>`).join('')}
  `).join('');

  btn.style.display = '';
  btn.disabled = false;
  btn.textContent = `Aplicar (0 de ${servicos.length})`;
  btn.onclick = aplicarClassificacaoEmLote;

  corpo.querySelectorAll('.lote-check').forEach(c => {
    c.addEventListener('change', () => atualizarContadorLote(servicos.length));
  });
  document.getElementById('btn-lote-todos').onclick = () => {
    const todos = corpo.querySelectorAll('.lote-check');
    const marcarTudo = [...todos].some(c => !c.checked);
    todos.forEach(c => { c.checked = marcarTudo; });
    atualizarContadorLote(servicos.length);
  };
}

function marcarPontosDaFicha(fichaId) {
  const corpo = document.getElementById('classificar-corpo');
  const daFicha = corpo.querySelectorAll(`.lote-check[data-ficha="${fichaId}"]`);
  const marcarTudo = [...daFicha].some(c => !c.checked);
  daFicha.forEach(c => { c.checked = marcarTudo; });
  atualizarContadorLote(corpo.querySelectorAll('.lote-check').length);
}

function atualizarContadorLote(total) {
  const marcados = document.querySelectorAll('.lote-check:checked').length;
  const btn = document.getElementById('btn-aplicar-lote');
  btn.textContent = `Aplicar (${marcados} de ${total})`;
  btn.disabled = marcados === 0;
}

async function aplicarClassificacaoEmLote() {
  const setorId = document.getElementById('lote-setor').value;
  if (!setorId) { toast('Escolha o setor a aplicar.', 'error'); return; }

  const ids = [...document.querySelectorAll('.lote-check:checked')].map(c => parseInt(c.value, 10));
  if (ids.length === 0) { toast('Marque ao menos um atendimento.', 'error'); return; }

  const btn = document.getElementById('btn-aplicar-lote');
  btn.disabled = true;
  btn.textContent = 'Aplicando...';

  try {
    const r = await api('/servicos/setor-em-lote', {
      method: 'PUT',
      body: JSON.stringify({ ids, setor_id: setorId }),
    });
    lembrarSetor(setorId);
    toast(r.mensagem, 'success');

    // Reabre em vez de fechar: quase sempre sobra outra frente para
    // classificar, e fechar obrigaria a navegar de volta.
    await abrirClassificacaoEmLote();
    await carregarVisaoGeral();
    if (fichaAtiva) await renderFichaDetalhe(fichaAtiva);
  } catch (e) {
    toast(e.message, 'error');
    btn.disabled = false;
  }
}

function copiarLinkTecnico(token) {
  if (!token) { toast('Esse técnico ainda não tem link — recarregue a página', 'error'); return; }
  const link = `${window.location.origin}/tecnico/${token}`;
  navigator.clipboard.writeText(link)
    .then(() => toast('Link do técnico copiado — mande por WhatsApp', 'success'))
    .catch(() => toast(link, 'info'));
}

// ─── Conversas com clientes (lado da empresa) ───────────────────────
//
// A mesma bolinha que o cliente vê, do outro lado do balcão. Duas telas
// dentro da mesma janela: a lista de conversas e a conversa aberta.
//
// Polling de 10s, não websocket: o servidor roda com 1 worker e 8 threads e
// cada conexão aberta prenderia uma thread (mesma razão do auto-refresh).
let chatSalaAberta = null;
let chatUltimoIdPainel = 0;
let chatModo = 'clientes';   // 'clientes' | 'equipe'
const chatIdsVistos = new Set();   // trava contra desenhar a mesma mensagem 2x
let chatBuscando = false;          // trava contra duas buscas ao mesmo tempo
let chatUltimaAtividade = 0;       // quando algo aconteceu na conversa
let chatTimer = null;

// RITMO ADAPTATIVO. Conversa viva precisa de resposta rápida; conversa
// parada não pode ficar consumindo servidor de um worker só. Logo depois
// de uma mensagem o chat pergunta de 3 em 3 segundos; passados 2 minutos
// sem nada, volta para 12 — e para de vez com a aba em segundo plano.
function _intervaloChat() {
  if (document.hidden) return 30000;
  return (Date.now() - chatUltimaAtividade < 120000) ? 3000 : 12000;
}

// Desenha a mensagem ANTES de o servidor confirmar. Sem isso o texto some
// do campo e não aparece em lugar nenhum até o próximo ciclo — a sensação
// exata de chat quebrado que o Kalebe relatou.
function _msgProvisoria(texto) {
  const corpo = document.getElementById('painel-chat-corpo');
  if (!corpo) return null;
  const div = document.createElement('div');
  div.className = 'msg minha enviando';
  div.innerHTML = `${esc(texto)}<span class="hora">enviando...</span>`;
  corpo.appendChild(div);
  corpo.scrollTop = corpo.scrollHeight;
  return div;
}

// Apagar conversa some com o registro do que foi combinado com o cliente —
// por isso confirma, e por isso o servidor só deixa admin fazer.
async function apagarConversa(ev, sala, cliente) {
  ev.stopPropagation();
  if (!confirm(`Apagar a conversa com ${cliente || 'este cliente'}?

As mensagens somem para os dois lados. O atendimento e o link continuam.`)) return;
  try {
    const r = await api(`/chat/${sala}`, { method: 'DELETE' });
    toast(r.mensagem, 'success');
    carregarConversas();
    atualizarBadgeChat();
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Chat da equipe ─────────────────────────────────────────────────
// Mesma janela, outra sala. Fica em rota PRÓPRIA no servidor (/api/equipe),
// e não em /api/chat/<sala>, porque aquele caminho é público — a conversa
// interna lá seria legível por qualquer um que digitasse o endereço.
async function abrirChatEquipe() {
  chatModo = 'equipe';
  chatSalaAberta = null;
  chatUltimoIdPainel = 0;
  chatIdsVistos.clear();

  const corpo = document.getElementById('painel-chat-corpo');
  const form = document.getElementById('painel-chat-form');
  document.getElementById('painel-chat-topo').innerHTML = `
    <div class="chat-abas">
      <button class="chat-aba" onclick="carregarConversas()">Clientes</button>
      <button class="chat-aba ativa" onclick="abrirChatEquipe()">Equipe</button>
    </div>
    <small>Conversa interna — o cliente não vê isto</small>`;
  corpo.innerHTML = '';
  form.style.display = 'flex';
  document.getElementById('painel-chat-texto').placeholder = 'Mensagem para a equipe...';

  await atualizarChatEquipe();
}

async function atualizarChatEquipe() {
  const corpo = document.getElementById('painel-chat-corpo');
  if (!corpo || chatModo !== 'equipe' || chatBuscando) return;
  chatBuscando = true;
  try {
    const d = await api(`/equipe/mensagens?desde=${chatUltimoIdPainel}`);
    (d.mensagens || []).forEach(m => {
      if (chatIdsVistos.has(m.id)) return;
      chatIdsVistos.add(m.id);
      // "minha" é a mensagem de quem está com a tela aberta.
      const minha = m.autor_nome === (usuarioLogado.nome || '');
      const tipo = m.autor_tipo === 'sistema' ? 'sistema' : (minha ? 'minha' : 'deles');
      const nome = tipo === 'deles' ? `<b>${esc(m.autor_nome || '')}</b><br>` : '';
      corpo.insertAdjacentHTML('beforeend',
        `<div class="msg ${tipo}">${nome}${esc(m.texto)}
           <span class="hora">${esc((m.criado_em || '').slice(11, 16))}</span></div>`);
      chatUltimoIdPainel = Math.max(chatUltimoIdPainel, m.id);
    });
    if ((d.mensagens || []).length) corpo.scrollTop = corpo.scrollHeight;
  } catch { /* sem rede: próximo ciclo */ }
  // finally é obrigatório: sem ele a trava ficaria presa para sempre na
  // primeira falha de rede, e o chat da equipe pararia de atualizar em
  // silêncio — que é o pior tipo de defeito neste sistema.
  finally { chatBuscando = false; }
}

function _msgHtml(m) {
  const tipo = m.autor_tipo === 'cliente' ? 'deles'
             : (m.autor_tipo === 'sistema' ? 'sistema' : 'minha');
  const nome = tipo === 'deles' && m.autor_nome ? `<b>${esc(m.autor_nome)}</b><br>` : '';
  return `<div class="msg ${tipo}">${nome}${esc(m.texto)}
            <span class="hora">${esc((m.criado_em || '').slice(11, 16))}</span></div>`;
}

async function carregarConversas() {
  const corpo = document.getElementById('painel-chat-corpo');
  const form = document.getElementById('painel-chat-form');
  const topo = document.getElementById('painel-chat-topo');
  if (!corpo) return;

  chatSalaAberta = null;
  chatModo = 'clientes';
  form.style.display = 'none';
  topo.innerHTML = `
    <div class="chat-abas">
      <button class="chat-aba ativa" onclick="carregarConversas()">Clientes</button>
      <button class="chat-aba" onclick="abrirChatEquipe()">Equipe</button>
    </div>`;

  let d;
  try { d = await api('/chat/conversas'); }
  catch (e) { corpo.innerHTML = `<div class="conversa-previa">${esc(e.message)}</div>`; return; }

  const cs = d.conversas || [];
  corpo.innerHTML = cs.length === 0
    ? `<div class="conversa-previa">Nenhuma conversa ainda. Elas aparecem quando o cliente escreve pelo link de acompanhamento.</div>`
    : cs.map(c => `
      <div class="conversa-item ${c.nao_lidas > 0 ? 'nova' : ''}">
        <div onclick="abrirConversa('${esc(c.sala)}', '${esc(c.cliente || '')}')">
          <div class="conversa-nome">${esc(c.cliente || 'Cliente')}
            ${c.nao_lidas > 0 ? `<span style="color:#ff8a8a">· ${c.nao_lidas} nova(s)</span>` : ''}</div>
          <div class="conversa-previa">${esc((c.ultima || {}).texto || '')}</div>
          <div class="conversa-previa">técnico ${esc(c.tecnico || '')}${c.ativo ? '' : ' · atendimento encerrado'}</div>
        </div>
        <button class="conversa-apagar" title="Apagar esta conversa"
                onclick="apagarConversa(event, '${esc(c.sala)}', '${esc(c.cliente || '')}')">
          ${icone('x', 'icone-11')}
        </button>
      </div>`).join('');
}

async function abrirConversa(sala, cliente) {
  chatSalaAberta = sala;
  chatUltimoIdPainel = 0;
  chatIdsVistos.clear();   // conversa nova, tela limpa

  const corpo = document.getElementById('painel-chat-corpo');
  const form = document.getElementById('painel-chat-form');
  document.getElementById('painel-chat-topo').innerHTML =
    `<span style="cursor:pointer" onclick="carregarConversas()">← ${esc(cliente || 'Cliente')}</span>
     <small>Responder como Porto Tec</small>`;
  corpo.innerHTML = '';
  form.style.display = 'flex';

  await atualizarConversaAberta();
  try { await api(`/chat/${sala}/lida`, { method: 'PUT' }); } catch {}
  atualizarBadgeChat();
}

async function atualizarConversaAberta() {
  if (!chatSalaAberta || chatBuscando) return;
  chatBuscando = true;
  const corpo = document.getElementById('painel-chat-corpo');
  try {
    const r = await fetch(`${BASE}/api/chat/${chatSalaAberta}?desde=${chatUltimoIdPainel}`,
                          { cache: 'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    let novas = 0;
    (d.mensagens || []).forEach(m => {
      if (chatIdsVistos.has(m.id)) return;   // ja esta na tela
      chatIdsVistos.add(m.id);
      corpo.insertAdjacentHTML('beforeend', _msgHtml(m));
      chatUltimoIdPainel = Math.max(chatUltimoIdPainel, m.id);
      chatUltimaAtividade = Date.now();
      novas++;
    });
    if (novas) corpo.scrollTop = corpo.scrollHeight;
  } catch { /* sem rede: próximo ciclo */ }
  finally { chatBuscando = false; }
}

// O contador vermelho é o que faz alguém abrir a janela. Sem ele, mensagem de
// cliente ficaria esperando alguém lembrar de olhar.
// O numero vem DE CARONA no /api/versao (ver _lerRevisao). Tinha polling
// proprio de 10s: com o painel aberto eram 12 pedidos por minuto por aba,
// num servidor de um worker so.
function pintarBadgeChat(n) {
  const badge = document.getElementById('painel-chat-badge');
  if (!badge) return;
  badge.textContent = n || 0;
  badge.classList.toggle('tem', (n || 0) > 0);
}

async function atualizarBadgeChat() {
  try { pintarBadgeChat((await api('/chat/conversas')).nao_lidas); } catch {}
}

function iniciarChatPainel() {
  const bolha = document.getElementById('painel-chat-bolha');
  const janela = document.getElementById('painel-chat-janela');
  const form = document.getElementById('painel-chat-form');
  if (!bolha) return;

  bolha.addEventListener('click', () => {
    const abrindo = !janela.classList.contains('aberto');
    janela.classList.toggle('aberto', abrindo);
    if (abrindo) carregarConversas();
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const campo = document.getElementById('painel-chat-texto');
    const texto = campo.value.trim();
    if (!texto) return;
    if (chatModo !== 'equipe' && !chatSalaAberta) return;
    campo.value = '';
    campo.focus();                    // continua digitando sem tirar a mão
    const provisoria = _msgProvisoria(texto);
    chatUltimaAtividade = Date.now();
    try {
      if (chatModo === 'equipe') {
        await api('/equipe/mensagens', { method: 'POST', body: JSON.stringify({ texto }) });
      } else {
        await api(`/chat/${chatSalaAberta}/responder`, {
          method: 'POST', body: JSON.stringify({ texto }),
        });
      }
      // A provisória sai e a de verdade entra pela busca — assim ela vem
      // com id e horário do servidor, e não duplica.
      if (provisoria) provisoria.remove();
      chatBuscando = false;   // libera a trava: esta busca não pode esperar
      if (chatModo === 'equipe') await atualizarChatEquipe();
      else await atualizarConversaAberta();
    } catch (err) {
      if (provisoria) provisoria.remove();
      campo.value = texto;  // devolve o texto: perder mensagem sem avisar é pior
      toast(err.message, 'error');
    }
  });

  // Com a janela FECHADA o contador chega pelo /api/versao, que já roda no
  // mesmo ritmo — aqui só trabalha quem está com a conversa aberta.
  //
  // setTimeout encadeado em vez de setInterval: o intervalo muda conforme a
  // conversa esquenta ou esfria, e setInterval não permite mudar o passo.
  (function ciclarChat() {
    const seguir = () => { chatTimer = setTimeout(ciclarChat, _intervaloChat()); };
    if (!janela.classList.contains('aberto')) return seguir();
    const p = (chatModo === 'equipe') ? atualizarChatEquipe()
            : (chatSalaAberta ? atualizarConversaAberta() : Promise.resolve());
    Promise.resolve(p).then(seguir, seguir);
  })();

  // Voltou para a aba: busca na hora, sem esperar o ciclo.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden || !janela.classList.contains('aberto')) return;
    chatBuscando = false;
    if (chatModo === 'equipe') atualizarChatEquipe();
    else if (chatSalaAberta) atualizarConversaAberta();
  });
}

// ─── Quem está logado, e o que essa pessoa pode ver ─────────────────
//
// O servidor JÁ bloqueia as rotas de administrador (ver _PREFIXOS_SO_ADMIN em
// app.py). Esconder aqui é sobre não oferecer o que a pessoa não pode usar —
// menu escondido sozinho seria decoração, porque quem souber o endereço entra
// do mesmo jeito.
//
// As 5 abas que mostra() controla (Diagnóstico/OS/Peças/Estoque/Cotação)
// nascem com display:none no HTML (ver templates/index.html) — de propósito,
// porque esta função só roda depois que /api/eu responde. Elas apareciam
// visíveis por padrão e SUMIAM quando a resposta chegava dizendo que a pessoa
// não podia: um "pisca" real pra quem tem menos permissão, mais visível com
// internet mais lenta (o motivo do Kalebe achar que só o login dele "não
// piscava" — o dele carrega rápido o bastante pra não notar). Nascer escondido
// e mostra() REVELAR em vez de esconder tira o pisca e ainda é mais seguro:
// falha ao carregar permissão deixa oculto, não visível.
let usuarioLogado = { papel: 'admin', nome: '', permissoes: {} };

// Atalho: a pessoa PODE fazer a ação? Admin cai em tudo true pelo servidor,
// então aqui é só ler o mapa que veio do /api/eu.
function podeUsuario(acao) {
  // Admin pode tudo (também protege contra a corrida antes do /api/eu chegar).
  if (usuarioLogado.papel === 'admin') return true;
  return !!(usuarioLogado.permissoes && usuarioLogado.permissoes[acao]);
}

async function carregarUsuarioLogado() {
  try { usuarioLogado = await api('/eu'); } catch { return; }
  usuarioLogado.permissoes = usuarioLogado.permissoes || {};

  const admin = usuarioLogado.papel === 'admin';
  // Cada aba aparece conforme a permissão (o servidor barra de qualquer jeito;
  // aqui é só não oferecer o que a pessoa não pode abrir).
  const mostra = (id, ok) => { const el = document.getElementById(id); if (el) el.style.display = ok ? '' : 'none'; };
  mostra('mtab-diagnostico', podeUsuario('diagnostico'));
  mostra('mtab-estoque', podeUsuario('estoque_ver'));
  mostra('mtab-pecas', podeUsuario('pecas'));
  mostra('mtab-os', podeUsuario('ordens_servico'));
  mostra('mtab-agendar', podeUsuario('ordens_servico'));
  mostra('cotacao-details', podeUsuario('cotacao'));

  const marca = document.getElementById('usuario-logado');
  if (marca) {
    marca.textContent = usuarioLogado.nome || '';
    marca.title = admin ? 'Administrador' : 'Técnico';
  }
}

// ─── Acessos (só admin, dentro da aba Diagnóstico) ──────────────────
let _acessosCache = [];   // usuários carregados, para o editor de permissões

async function carregarAcessos() {
  const alvo = document.getElementById('acessos-corpo');
  if (!alvo) return;

  let d;
  try { d = await api('/usuarios'); }
  catch (e) { alvo.innerHTML = `<div class="diag-detalhe">${esc(e.message)}</div>`; return; }

  _acessosCache = d.usuarios || [];
  alvo.innerHTML = `
    ${_acessosCache.map(u => {
      const admin = u.papel === 'admin';
      // Conta quantas ações o técnico tem liberadas — resumo rápido na linha.
      const liberadas = Object.values(u.permissoes || {}).filter(Boolean).length;
      return `
      <div class="diag-item">
        <div class="diag-titulo">${esc(u.nome)}
          <span class="diag-detalhe" style="grid-column:auto;">${esc(u.login)}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
          ${_selo(admin ? 'ok' : 'aviso', admin ? 'administrador' : 'técnico')}
          ${admin ? '' : `<span class="diag-detalhe" style="grid-column:auto;">${liberadas} permiss${liberadas === 1 ? 'ão' : 'ões'}</span>`}
          ${admin ? '' : `<button class="btn btn-primary btn-sm" onclick="abrirEditorPermissoes(${u.id})">Permissões</button>`}
          ${admin ? '' : `<button class="btn btn-ghost btn-sm" onclick="liberarTudo(${u.id}, '${esc(u.nome)}')" title="Marca todas as permissões do catálogo pra essa pessoa, sem abrir o editor">Liberar tudo</button>`}
          <button class="btn btn-ghost btn-sm" onclick="trocarSenhaUsuario(${u.id}, '${esc(u.nome)}')">Trocar senha</button>
          <button class="btn btn-ghost btn-sm" onclick="removerUsuario(${u.id}, '${esc(u.nome)}')">Remover</button>
        </div>
        <div class="diag-detalhe">
          ${u.tecnico_nome ? 'ligado ao técnico ' + esc(u.tecnico_nome) + ' · ' : ''}
          ${u.ultimo_acesso ? 'último acesso ' + esc(u.ultimo_acesso) : 'nunca entrou'}
        </div>
      </div>`;
    }).join('')}
    <button class="btn btn-primary btn-sm" style="margin-top:10px;"
            onclick="criarUsuario()">+ Novo acesso</button>`;
}

// Atalho pra "essa pessoa está travada em tudo, só me deixa ela ver o site
// inteiro": marca TODAS as ações do catálogo de uma vez, sem precisar abrir
// o editor e clicar item por item. Existe porque criar um acesso novo já
// nasce sem nenhuma permissão (PADRAO_TECNICO é vazio de propósito), e até
// alguém lembrar de configurar cada área, a pessoa não consegue fazer nada
// no site — o que por fora parece "o site tá travado", quando na verdade
// é falta de permissão nunca dada, não bug nenhum.
async function liberarTudo(usuarioId, nome) {
  if (!confirm(`Liberar TODAS as permissões pra ${nome}? Dá pra restringir de novo depois pelo editor.`)) return;
  if (!_permCatalogo) {
    try { _permCatalogo = (await api('/permissoes/catalogo')).catalogo || []; }
    catch (e) { toast(e.message, 'error'); return; }
  }
  const perms = {};
  _permCatalogo.forEach(c => { perms[c.chave] = true; });
  try {
    await api(`/usuarios/${usuarioId}/permissoes`, { method: 'PUT',
      body: JSON.stringify({ permissoes: perms }) });
    toast(`${nome} agora vê tudo`, 'success');
    carregarAcessos();
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Editor de permissões (drawer lateral) ──────────────────────────────
let _permCatalogo = null;   // catálogo de ações, buscado uma vez
let _permUsuarioId = null;

async function abrirEditorPermissoes(usuarioId) {
  _permUsuarioId = usuarioId;
  const u = _acessosCache.find(x => x.id === usuarioId);
  if (!u) return;
  if (!_permCatalogo) {
    try { _permCatalogo = (await api('/permissoes/catalogo')).catalogo || []; }
    catch (e) { toast(e.message, 'error'); return; }
  }

  document.getElementById('perm-drawer-nome').textContent = u.nome;
  const perms = u.permissoes || {};

  // Agrupa por área para ficar legível.
  const areas = {};
  _permCatalogo.forEach(c => { (areas[c.area] = areas[c.area] || []).push(c); });
  document.getElementById('perm-drawer-corpo').innerHTML = `
    <label class="perm-linha" style="border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:4px;">
      <input type="checkbox" id="perm-marcar-todas"
             onchange="document.querySelectorAll('#perm-drawer-corpo .perm-check').forEach(ch => ch.checked = this.checked)">
      <span><b>Marcar todas</b></span>
    </label>
  ` + Object.entries(areas).map(([area, itens]) => `
    <div class="perm-area">
      <div class="perm-area-titulo">${esc(area)}</div>
      ${itens.map(c => `
        <label class="perm-linha">
          <input type="checkbox" class="perm-check" data-acao="${esc(c.chave)}" ${perms[c.chave] ? 'checked' : ''}>
          <span>${esc(c.rotulo)}</span>
        </label>`).join('')}
    </div>`).join('');

  document.getElementById('drawer-permissoes').classList.add('aberto');
}

function fecharEditorPermissoes() {
  document.getElementById('drawer-permissoes').classList.remove('aberto');
}

async function salvarPermissoes() {
  const btn = document.getElementById('perm-salvar-btn');
  const perms = {};
  document.querySelectorAll('#perm-drawer-corpo .perm-check').forEach(ch => {
    perms[ch.dataset.acao] = ch.checked;
  });
  btn.disabled = true;
  try {
    await api(`/usuarios/${_permUsuarioId}/permissoes`, { method: 'PUT',
      body: JSON.stringify({ permissoes: perms }) });
    toast('Permissões salvas.', 'success');
    fecharEditorPermissoes();
    carregarAcessos();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function criarUsuario() {
  const nome = prompt('Nome da pessoa:');
  if (!nome) return;
  const login = prompt('Usuário para entrar (sem espaço):');
  if (!login) return;
  const senha = prompt('Senha (mínimo 6 caracteres):');
  if (!senha) return;
  const ehAdmin = confirm('Este acesso é de ADMINISTRADOR?\n\nOK = administrador (vê tudo)\nCancelar = técnico (não vê diagnóstico)');

  let tecnico_id = null;
  if (!ehAdmin && (tecnicos || []).length) {
    const lista = tecnicos.map((t, i) => `${i + 1}) ${t.nome}`).join('\n');
    const r = prompt(`Ligar a qual técnico das rotas? (deixe vazio para nenhum)\n\n${lista}`);
    const idx = parseInt(r, 10) - 1;
    if (idx >= 0 && idx < tecnicos.length) tecnico_id = tecnicos[idx].id;
  }

  try {
    await api('/usuarios', { method: 'POST', body: JSON.stringify({
      nome, login, senha, papel: ehAdmin ? 'admin' : 'tecnico', tecnico_id }) });
    toast('Acesso criado', 'success');
    carregarAcessos();
  } catch (e) { toast(e.message, 'error'); }
}

async function trocarSenhaUsuario(id, nome) {
  const senha = prompt(`Nova senha para ${nome} (mínimo 6 caracteres):`);
  if (!senha) return;
  try {
    await api(`/usuarios/${id}`, { method: 'PUT', body: JSON.stringify({ senha }) });
    toast('Senha trocada', 'success');
  } catch (e) { toast(e.message, 'error'); }
}

async function removerUsuario(id, nome) {
  if (!confirm(`Remover o acesso de ${nome}?`)) return;
  try {
    await api(`/usuarios/${id}`, { method: 'DELETE' });
    toast('Acesso removido', 'success');
    carregarAcessos();
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Aba Diagnóstico: saúde do sistema numa tela ────────────────────
//
// Existe para o Kalebe parar de me perguntar "está funcionando?". Cada um
// destes sinais já existia como endereço solto de JSON; o que faltava era
// juntar e traduzir para linguagem de gente.

function _selo(estado, texto) {
  return `<span class="diag-selo ${estado}">${esc(texto)}</span>`;
}

function _linhaDiag(titulo, estado, texto, detalhe = '') {
  return `
    <div class="diag-item">
      <div class="diag-titulo">${esc(titulo)}</div>
      <div>${_selo(estado, texto)}</div>
      ${detalhe ? `<div class="diag-detalhe">${detalhe}</div>` : ''}
    </div>`;
}

async function carregarDiagnostico() {
  const alvo = document.getElementById('diagnostico-corpo');
  if (!alvo) return;
  alvo.innerHTML = `<div class="loading-row" style="display:flex;gap:10px;padding:20px;"><div class="spinner"></div> Conferindo tudo...</div>`;

  let d;
  try {
    d = await api('/diagnostico/geral', {}, 90000);
  } catch (e) {
    alvo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const partes = [];

  // ── Aparelhos dos técnicos (é o que mais deu trabalho até hoje)
  const ap = (d.rastreio && d.rastreio.aparelhos) || [];
  partes.push(`<div class="diag-secao">Celular dos técnicos</div>`);
  if (ap.length === 0) {
    partes.push(_linhaDiag('Nenhum técnico', 'aviso', 'sem cadastro'));
  } else {
    ap.forEach(a => {
      const ok = /enviando|tudo certo/i.test(a.situacao || '');
      const grave = /BLOQUEADA|VELHO|nunca reportou/i.test(a.situacao || '');
      partes.push(_linhaDiag(
        a.tecnico,
        ok ? 'ok' : (grave ? 'ruim' : 'aviso'),
        a.situacao || '—',
        a.visto_em ? `visto em ${esc(a.visto_em)} · versão ${esc(a.app_versao || '—')}` : ''));
    });
  }

  // ── Integrações
  partes.push(`<div class="diag-secao">Integrações</div>`);

  const ag = d.agoraos || {};
  if (ag.erro) {
    partes.push(_linhaDiag('AgoraOS', 'ruim', 'falhou', esc(ag.erro)));
  } else if (!ag.configurada) {
    partes.push(_linhaDiag('AgoraOS', 'aviso', 'não configurado',
      'Falta: ' + esc((ag.faltando || []).join(', ') || 'credenciais')));
  } else if (!ag.conectou) {
    partes.push(_linhaDiag('AgoraOS', 'ruim', 'não conectou', esc(ag.erro || '')));
  } else {
    partes.push(_linhaDiag('AgoraOS', ag.estoque_efetivo ? 'ok' : 'aviso',
      ag.estoque_efetivo ? 'baixa de estoque ativa' : 'conectado, mas sem controle de estoque',
      `${ag.produtos} produtos · ${ag.os} OS · ${ag.produtos_com_estoque_ligado} com estoque ligado`));
  }

  const pl = (d.planilha && d.planilha.planilha) || {};
  const em = (d.planilha && d.planilha.email) || {};
  partes.push(_linhaDiag('Planilha de peças',
    pl.configurada ? 'ok' : 'aviso',
    pl.configurada ? 'configurada' : 'faltam variáveis',
    esc((pl.faltando || []).join(', '))));
  partes.push(_linhaDiag('Leitura das notas (e-mail)',
    em.configurado ? 'ok' : 'aviso',
    em.configurado ? 'configurada' : 'não configurada'));

  const ia = d.ia || {};
  partes.push(_linhaDiag('Análise de erros com IA',
    ia.configurado ? 'ok' : 'aviso',
    ia.configurado ? 'ligada (' + esc(ia.modelo || '') + ')' : 'sem ANTHROPIC_API_KEY',
    ia.configurado ? '' : 'Defina ANTHROPIC_API_KEY nas variáveis do Railway para o botão "Analisar com IA" funcionar.'));

  // ── Higiene dos dados
  partes.push(`<div class="diag-secao">Dados</div>`);
  const semSetor = (d.setores && d.setores.sem_setor) || 0;
  partes.push(_linhaDiag('Atendimentos sem setor',
    semSetor === 0 ? 'ok' : 'aviso',
    semSetor === 0 ? 'todos classificados' : `${semSetor} sem classificação`,
    semSetor ? `<button class="btn btn-primary btn-sm" onclick="abrirClassificacaoEmLote()">Classificar agora</button>` : ''));

  partes.push(_linhaDiag('Chave de sessão',
    d.secret_fixa ? 'ok' : 'ruim',
    d.secret_fixa ? 'fixa (sessão sobrevive a atualização)' : 'temporária — todo deploy desloga',
    d.secret_fixa ? '' : 'Defina SECRET_KEY nas variáveis do Railway.'));

  // ── Erros de navegador (agora EDITÁVEIS: status, observação, excluir)
  const er = d.erros || {};
  const abertos = er.abertos != null ? er.abertos : er.total;
  partes.push(`<div class="diag-secao">Erros na tela ${er.total ? `· ${abertos} em aberto` : ''}
    ${er.total && podeUsuario('diagnostico_editar') ? `<button class="btn btn-ghost btn-xs" style="float:right;" onclick="limparErrosResolvidos()">Limpar tratados</button>` : ''}</div>`);
  if (!er.total) {
    partes.push(_linhaDiag('Nenhum erro registrado', 'ok', 'limpo'));
  } else {
    partes.push((er.ultimos || []).map(e => _renderErroDiag(e)).join(''));
  }

  alvo.innerHTML = `<div class="diag-versao">Sistema na versão ${esc(d.app || '—')}</div>`
    + partes.join('')
    // Acessos só para quem pode gerenciar usuários.
    + (podeUsuario('gerenciar_usuarios')
        ? `<div class="diag-secao">Acessos ao sistema</div><div id="acessos-corpo"></div>`
        : '');
  if (podeUsuario('gerenciar_usuarios')) carregarAcessos();
}

// Cada erro do log com status editável, observação e excluir. `data-id` liga
// os controles ao registro; salvar é na hora, ao mudar o campo.
const _STATUS_ERRO_DIAG = ['novo', 'investigando', 'resolvido', 'ignorado'];
function _renderErroDiag(e) {
  const st = e.status || 'novo';
  const opts = _STATUS_ERRO_DIAG.map(s =>
    `<option value="${s}" ${s === st ? 'selected' : ''}>${s}</option>`).join('');
  const podeEditar = podeUsuario('diagnostico_editar');
  return `
    <div class="diag-erro diag-erro--${esc(st)}" data-erro="${e.id}">
      <div class="diag-erro-msg">${esc(e.mensagem)}</div>
      <div class="diag-detalhe">${esc(e.quando)} · ${esc(e.origem)} · ${esc(e.versao)} · ${esc(e.url)}</div>
      <div class="diag-erro-acoes">
        <button class="btn btn-ghost btn-xs diag-ia-btn" onclick="analisarErroIA(${e.id})" title="Pedir à IA um diagnóstico e a correção">🤖 Analisar com IA</button>
        ${podeEditar ? `
        <select class="diag-erro-status" onchange="atualizarErroDiag(${e.id}, 'status', this.value)">${opts}</select>
        <input class="diag-erro-obs form-input" placeholder="observação..." value="${esc(e.obs || '')}"
               onchange="atualizarErroDiag(${e.id}, 'obs', this.value)">
        <button class="btn btn-ghost btn-xs estoque-btn-excluir" onclick="removerErroDiag(${e.id})">Excluir</button>` : ''}
      </div>
      <div class="diag-ia-resultado" id="diag-ia-${e.id}"></div>
    </div>`;
}

async function analisarErroIA(id) {
  const alvo = document.getElementById(`diag-ia-${id}`);
  if (!alvo) return;
  alvo.innerHTML = '<div class="diag-ia-carregando"><div class="spinner"></div> A IA está analisando o erro...</div>';
  try {
    const d = await api(`/erros-cliente/${id}/analisar`, { method: 'POST' }, 90000);
    // Texto simples da IA — escapo e preservo as quebras de linha.
    alvo.innerHTML = `<div class="diag-ia-caixa"><div class="diag-ia-titulo">🤖 Análise da IA</div><div class="diag-ia-texto">${esc(d.analise).replace(/\n/g, '<br>')}</div></div>`;
  } catch (e) {
    alvo.innerHTML = `<div class="erro-box">${esc(e.message)}</div>`;
  }
}

async function atualizarErroDiag(id, campo, valor) {
  try {
    await api(`/erros-cliente/${id}`, { method: 'PUT', body: JSON.stringify({ [campo]: valor }) });
    // Reflete a cor do status na hora sem recarregar tudo.
    if (campo === 'status') {
      const box = document.querySelector(`.diag-erro[data-erro="${id}"]`);
      if (box) box.className = `diag-erro diag-erro--${valor}`, box.dataset.erro = id;
    }
    toast('Diagnóstico atualizado.', 'success');
  } catch (e) { toast(e.message, 'error'); }
}

async function removerErroDiag(id) {
  if (!confirm('Excluir este registro de erro?')) return;
  try {
    await api(`/erros-cliente/${id}`, { method: 'DELETE' });
    document.querySelector(`.diag-erro[data-erro="${id}"]`)?.remove();
    toast('Registro removido.', 'success');
  } catch (e) { toast(e.message, 'error'); }
}

async function limparErrosResolvidos() {
  if (!confirm('Limpar todos os erros marcados como resolvidos/ignorados?')) return;
  try {
    const r = await api('/erros-cliente/resolvidos', { method: 'DELETE' });
    toast(`${r.removidos || 0} registro(s) limpos.`, 'success');
    carregarDiagnostico();
  } catch (e) { toast(e.message, 'error'); }
}


// ─── Aviso de pontos sem setor ──────────────────────────────────────
// O relatório por setor é o número que serve para cobrar a fabricante. Com
// 60% dos pontos sem classificação ele não vale nada — e ninguém classifica
// o que não aparece na frente.
// Faixa de avisos no topo do painel.
//
// Passou a ler `/avisos` em vez de `/setores/resumo`: a mesma chamada agora
// traz também os atendimentos em que o CLIENTE ESTÁ OLHANDO UM MAPA PARADO.
// Isso nasceu de um caso real — o celular do técnico parou de mandar posição
// às 17h e ninguém percebeu até o checkup do dia seguinte; quem descobriria
// primeiro seria o cliente. Sem custo extra de rede: uma chamada no lugar da
// outra (o servidor roda com um worker só, ver siteroteiro-desempenho).
async function verificarPontosSemSetor() {
  let d;
  try { d = await api('/avisos'); } catch { return; }

  const semSetor = d.sem_setor || 0;
  const mudos = d.rastreio || [];

  let faixa = document.getElementById('aviso-sem-setor');
  if (!semSetor && mudos.length === 0) { if (faixa) faixa.remove(); return; }

  if (!faixa) {
    faixa = document.createElement('div');
    faixa.id = 'aviso-sem-setor';
    faixa.className = 'aviso-sem-setor';
    const main = document.getElementById('panel-roteiros-main');
    if (main) main.prepend(faixa); else return;
  }

  const partes = [];

  // O rastreio vem primeiro: é o que o cliente está vendo AGORA.
  if (mudos.length) {
    partes.push(`
      <div class="aviso-linha grave">
        <span>${mudos.map(m => `<b>${esc(m.cliente)}</b> não está vendo
          ${esc(m.tecnico)} no mapa (${esc(m.motivo)})`).join(' · ')}</span>
        <button class="btn btn-ghost btn-sm" onclick="switchMainTab('diagnostico')">Ver diagnóstico</button>
      </div>`);
  }

  if (semSetor) {
    partes.push(`
      <div class="aviso-linha">
        <span><b>${semSetor}</b> atendimento${semSetor !== 1 ? 's' : ''} sem setor —
          o relatório por frente fica incompleto enquanto isso.</span>
        <button class="btn btn-primary btn-sm" onclick="abrirClassificacaoEmLote()">Classificar</button>
      </div>`);
  }

  faixa.innerHTML = partes.join('');
}


// ─── Comparativo entre técnicos ─────────────────────────────────────
// Passou a fazer sentido com dois técnicos em campo: mostra quem está
// sobrecarregado e quanto cada rota custa em estrada.
async function carregarComparativoTecnicos() {
  const alvo = document.getElementById('comparativo-tecnicos');
  if (!alvo) return;

  let d;
  try { d = await api('/relatorios/tecnicos'); }
  catch (e) { alvo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`; return; }

  const ts = d.tecnicos || [];
  if (ts.length === 0) { alvo.innerHTML = ''; return; }

  alvo.innerHTML = `
    <div class="conc-titulo" style="margin-bottom:10px;">Comparativo entre técnicos (${d.dias} dias)</div>
    <div class="comp-grade">
      ${ts.map(t => `
        <div class="comp-card" style="border-left:3px solid ${escCor(t.cor)}">
          <div class="comp-topo">
            ${t.foto ? `<img src="${t.foto}" class="tec-avatar" alt="">`
                     : `<div class="tec-avatar sem-foto" style="background:${escCor(t.cor)}">${esc((t.nome||'?').charAt(0).toUpperCase())}</div>`}
            <div class="comp-nome">${esc(t.nome)}</div>
            <div class="comp-fatia">${t.fatia}% da carga</div>
          </div>
          <div class="comp-numeros">
            <div><b>${t.pontos}</b><span>atendimentos</span></div>
            <div><b>${t.pendentes}</b><span>a fazer</span></div>
            <div><b>${t.km}</b><span>km</span></div>
            <div><b>${t.km_por_ponto}</b><span>km por atend.</span></div>
            <div><b>${t.taxa_conclusao}%</b><span>concluído</span></div>
            <div><b>${t.rotas}</b><span>rotas</span></div>
          </div>
          <div class="comp-barra"><span style="width:${Math.min(100, t.fatia)}%;background:${escCor(t.cor)}"></span></div>
        </div>`).join('')}
    </div>
    <div class="diag-detalhe" style="margin-top:8px;">
      <b>km por atendimento</b> é o número que compara de verdade: quilometragem alta com
      muitos pontos é rota cheia; alta com poucos é rota espalhada, que é a que
      pesa no combustível.
    </div>`;
}


// ─── Transferir trabalho entre técnicos ─────────────────────────────
//
// Nasceu de um caso real: a Porto Tec passou a ter dois técnicos e TODAS as
// fichas estavam no nome de um só. O Igor saiu para atender, mandou o "a
// caminho", e o cliente não via ninguém — porque o rastreio é por técnico e o
// atendimento pertencia ao Pedro. Sem transferência, a única saída era
// refazer a rota do zero no outro nome.

function _escolherTecnico(excetoId, titulo) {
  const opcoes = (tecnicos || []).filter(t => t.id !== excetoId);
  if (opcoes.length === 0) {
    toast('Não há outro técnico cadastrado para receber', 'error');
    return null;
  }
  // prompt numerado em vez de modal: são dois ou três técnicos, e uma janela
  // inteira para escolher entre dois nomes é mais atrito do que ajuda.
  const lista = opcoes.map((t, i) => `${i + 1}) ${t.nome}`).join('\n');
  const resp = prompt(`${titulo}\n\n${lista}\n\nDigite o número:`);
  if (resp === null) return null;

  const idx = parseInt(resp, 10) - 1;
  if (!(idx >= 0 && idx < opcoes.length)) {
    toast('Escolha inválida', 'error');
    return null;
  }
  return opcoes[idx];
}

async function transferirPonto(servicoId, nomeCliente) {
  const ponto = (fichaAtiva?.servicos || []).find(s => s.id === servicoId);
  const donoAtual = fichaAtiva?.ficha?.tecnico_id;
  const destino = _escolherTecnico(donoAtual, `Passar "${nomeCliente}" para qual técnico?`);
  if (!destino) return;

  try {
    const r = await api(`/servicos/${servicoId}/tecnico`, {
      method: 'PUT', body: JSON.stringify({ tecnico_id: destino.id }),
    });
    toast(r.mensagem, 'success');
    await carregarTecnicos();
    if (fichaAtiva) await renderFichaDetalhe(fichaAtiva);
  } catch (e) { toast(e.message, 'error'); }
}

async function transferirFicha(fichaId) {
  const donoAtual = fichaAtiva?.ficha?.tecnico_id;
  const destino = _escolherTecnico(donoAtual, 'Passar a rota inteira para qual técnico?');
  if (!destino) return;

  if (!confirm(`Transferir a rota inteira para ${destino.nome}?`)) return;

  try {
    const r = await api(`/fichas/${fichaId}/tecnico`, {
      method: 'PUT', body: JSON.stringify({ tecnico_id: destino.id }),
    });
    toast(r.mensagem, 'success');
    await carregarTecnicos();
    if (fichaAtiva) await renderFichaDetalhe(fichaAtiva);
  } catch (e) { toast(e.message, 'error'); }
}


// ─── Recolher a lista de fichas de cada técnico ─────────────────────
//
// Com três ou quatro técnicos e uma ficha por dia da semana, a barra lateral
// vira uma coluna sem fim e ninguém acha nada. Recolhido, o técnico continua
// visível — some só a lista de dias dele.
//
// O estado fica no localStorage, POR TÉCNICO: a sidebar é redesenhada a cada
// auto-refresh (a cada 10s) e, sem guardar, tudo o que o Kalebe recolhesse
// voltaria a abrir sozinho no ciclo seguinte.
const CHAVE_RECOLHIDOS = 'portotec:tecnicos-recolhidos';

function _lerRecolhidos() {
  try { return new Set(JSON.parse(localStorage.getItem(CHAVE_RECOLHIDOS)) || []); }
  catch { return new Set(); }
}

function tecnicoRecolhido(id) {
  return _lerRecolhidos().has(String(id));
}

function alternarTecnico(id) {
  const secao = document.getElementById(`tecnico-section-${id}`);
  if (!secao) return;

  const recolhidos = _lerRecolhidos();
  const virouRecolhido = !secao.classList.contains('recolhido');

  secao.classList.toggle('recolhido', virouRecolhido);
  if (virouRecolhido) recolhidos.add(String(id));
  else recolhidos.delete(String(id));

  localStorage.setItem(CHAVE_RECOLHIDOS, JSON.stringify([...recolhidos]));
}

// Recolher ou abrir todos de uma vez — útil no começo do dia, quando só
// interessa o técnico que está em rota.
function alternarTodosTecnicos() {
  const todos = (tecnicos || []).map(t => String(t.id));
  const algumAberto = todos.some(id => !tecnicoRecolhido(id));

  localStorage.setItem(CHAVE_RECOLHIDOS, JSON.stringify(algumAberto ? todos : []));
  todos.forEach(id => {
    const secao = document.getElementById(`tecnico-section-${id}`);
    if (secao) secao.classList.toggle('recolhido', algumAberto);
  });

  const btn = document.getElementById('btn-recolher-todos');
  if (btn) btn.title = algumAberto ? 'Abrir todos' : 'Recolher todos';
}

// Quantas fichas o técnico tem, mostrado no cabeçalho. Recolher não pode
// esconder informação: o número diz o que ficou escondido ali dentro.
function atualizarContagemTecnico(tecnicoId, quantas) {
  const alvo = document.getElementById(`tec-contagem-${tecnicoId}`);
  if (alvo) alvo.textContent = quantas ? `${quantas}` : '';
}


// ─── Foto de perfil do técnico ──────────────────────────────────────
//
// A foto vai para o BANCO como data URI, não para uma pasta: o disco do
// Railway é apagado a cada deploy e a foto sumiria sem ninguém ligar uma
// coisa à outra. Para caber, o navegador reduz a imagem ANTES de enviar —
// foto de celular tem 4 MB e chegaria como 5,5 MB em base64.

// A foto NÃO vem mais na listagem de técnicos: era um data URI de ~30 KB por
// pessoa, e a listagem é rebaixada a cada auto-refresh — 62 KB de rede a cada
// ciclo para uma imagem que não muda. Agora vem de rota própria, com cache de
// 1 hora no navegador, e fica guardada aqui para o resto da sessão.
const _fotosCache = {};

function avatarTecnico(t) {
  const inicial = (t.nome || '?').trim().charAt(0).toUpperCase();
  const src = t.foto || _fotosCache[t.id];

  if (src) {
    return `<img src="${src}" class="tec-avatar" alt=""
              onclick="escolherFotoTecnico(${t.id})" title="Trocar foto">`;
  }

  // Sem a foto em mãos, desenha a inicial AGORA e busca a imagem em paralelo —
  // esperar a foto para desenhar a barra lateral deixaria a tela em branco por
  // causa de um enfeite.
  if (t.tem_foto) carregarFotoTecnico(t.id);

  return `<div class="tec-avatar sem-foto" data-tecnico="${t.id}"
            style="background:${escCor(t.cor)}"
            onclick="escolherFotoTecnico(${t.id})"
            title="${t.tem_foto ? 'Carregando foto...' : 'Adicionar foto'}">${esc(inicial)}</div>`;
}

async function carregarFotoTecnico(id) {
  if (_fotosCache[id] === undefined) _fotosCache[id] = null;  // evita buscar 2x
  else return;

  try {
    const d = await api(`/tecnicos/${id}/foto`);
    _fotosCache[id] = d.foto;
    // Troca só os avatares daquele técnico que já estão na tela, sem
    // redesenhar a barra lateral inteira.
    document.querySelectorAll(`.tec-avatar[data-tecnico="${id}"]`).forEach(el => {
      const img = document.createElement('img');
      img.src = d.foto;
      img.className = 'tec-avatar';
      img.title = 'Trocar foto';
      img.onclick = () => escolherFotoTecnico(id);
      el.replaceWith(img);
    });
  } catch {
    _fotosCache[id] = null;   // sem foto: fica a inicial colorida
  }
}

// Reduz para um quadrado de 256px em JPEG. O recorte é central e mantém a
// proporção: esticar rosto para caber num quadrado fica ruim em qualquer foto.
//
// DUAS TENTATIVAS, e a segunda é o que faz foto de iPhone funcionar:
// o iPhone salva em HEIC por padrão, e a maioria dos navegadores NÃO decodifica
// HEIC pela tag <img> — a imagem simplesmente não carrega e o erro morre calado.
// O createImageBitmap aceita mais formatos e serve de rede de segurança.
// Quando os dois falham, a mensagem diz o que fazer, em vez de sumir.
async function reduzirImagem(arquivo, lado = 256, qualidade = 0.82) {
  const desenhar = (fonte, largura, altura) => {
    const corte = Math.min(largura, altura);
    const cv = document.createElement('canvas');
    cv.width = cv.height = lado;
    const ctx = cv.getContext('2d');
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(fonte, (largura - corte) / 2, (altura - corte) / 2,
                  corte, corte, 0, 0, lado, lado);
    return cv.toDataURL('image/jpeg', qualidade);
  };

  // Caminho 1: createImageBitmap — mais tolerante a formato.
  if (typeof createImageBitmap === 'function') {
    try {
      const bmp = await createImageBitmap(arquivo);
      const url = desenhar(bmp, bmp.width, bmp.height);
      bmp.close && bmp.close();
      return url;
    } catch { /* cai para o caminho 2 */ }
  }

  // Caminho 2: <img> com objectURL. Funciona onde o de cima não existe.
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(arquivo);
    const img = new Image();
    img.onload = () => {
      try { resolve(desenhar(img, img.naturalWidth, img.naturalHeight)); }
      catch (e) { reject(new Error('Não consegui processar a imagem: ' + e.message)); }
      finally { URL.revokeObjectURL(url); }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      const nome = (arquivo.name || '').toLowerCase();
      reject(new Error(
        nome.endsWith('.heic') || nome.endsWith('.heif')
          ? 'Foto em HEIC (formato do iPhone) — o navegador não abre esse tipo. '
            + 'No iPhone: Ajustes > Câmera > Formatos > "Mais compatível". '
            + 'Ou tire um print da foto e envie o print.'
          : 'Esse arquivo não é uma imagem que o navegador consiga abrir.'));
    };
    img.src = url;
  });
}

function escolherFotoTecnico(tecnicoId) {
  const entrada = document.createElement('input');
  entrada.type = 'file';
  entrada.accept = 'image/*';
  // Fora do documento, alguns navegadores descartam o elemento antes do
  // change disparar e a escolha do arquivo se perde sem erro nenhum.
  entrada.style.display = 'none';
  document.body.appendChild(entrada);

  entrada.onchange = async () => {
    const arquivo = entrada.files && entrada.files[0];
    entrada.remove();
    if (!arquivo) return;

    // Cada etapa avisa. Antes, qualquer falha aqui era silêncio absoluto —
    // o Kalebe escolhia a foto e "não dava em nada".
    toast('Preparando a foto...', 'info');
    let foto;
    try {
      foto = await reduzirImagem(arquivo);
    } catch (e) {
      toast(e.message, 'error');
      return;
    }

    try {
      await api(`/tecnicos/${tecnicoId}/foto`, {
        method: 'PUT', body: JSON.stringify({ foto }),
      });
    } catch (e) {
      toast('Falha ao gravar: ' + e.message, 'error');
      return;
    }

    delete _fotosCache[tecnicoId];
    toast('Foto atualizada', 'success');
    await carregarTecnicos();
  };

  entrada.click();
}

async function removerFotoTecnico(tecnicoId) {
  if (!confirm('Remover a foto deste técnico?')) return;
  try {
    await api(`/tecnicos/${tecnicoId}/foto`, {
      method: 'PUT', body: JSON.stringify({ foto: '' }),
    });
    delete _fotosCache[tecnicoId];
    toast('Foto removida', 'success');
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Rastreador por técnico ─────────────────────────────────────────
// Cada técnico tem o SEU endereço, com o próprio token: é isso que separa a
// posição do Pedro da do Igor. Colar o endereço errado no aparelho faria um
// aparecer no lugar do outro, então a tela entrega o endereço pronto para
// copiar em vez de deixar alguém montar na mão.
function abrirRastreadorTecnico(tecnicoId) {
  const t = (tecnicos || []).find(x => x.id === tecnicoId);
  if (!t) return;

  const url = `${location.origin}/api/t/${t.token}/rastreador`;
  const corpo = document.getElementById('rastreador-corpo');

  corpo.innerHTML = `
    <div class="conc-item" style="align-items:center;">
      ${avatarTecnico(t)}
      <div style="flex:1;min-width:0;">
        <div class="conc-cliente">${esc(t.nome)}</div>
        <div class="conc-meta">Endereço exclusivo deste técnico</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="removerFotoTecnico(${t.id})"
              ${t.foto ? '' : 'disabled'}>Remover foto</button>
    </div>

    <div class="conc-titulo" style="margin-top:14px;">Endereço para o OwnTracks</div>
    <input class="input" id="rastreador-url" readonly value="${esc(url)}"
           style="font-size:11px;" onclick="this.select()">
    <button class="btn btn-primary btn-sm" style="margin-top:8px;"
            onclick="copiarTexto('${esc(url)}')">Copiar endereço</button>

    <div class="conc-titulo" style="margin-top:16px;">No aplicativo do celular</div>
    <div class="conc-meta" style="line-height:1.7;">
      <b>Preferences → Connection → Mode:</b> HTTP<br>
      <b>Host/URL:</b> o endereço acima<br>
      <b>Username e Password:</b> <b>${esc((t.nome || 'tec').split(' ')[0].toLowerCase())}</b>
      — preencha os dois, o app não envia com eles vazios<br>
      <b>Device ID:</b> ${esc((t.nome || 'tec').split(' ')[0].toLowerCase())}<br>
      <b>Advanced:</b> intervalo 30s · deslocamento 50m · modo <b>Move</b><br>
      Permissão de localização: <b>o tempo todo</b>. No Android, não dispense
      a notificação fixa do aplicativo — é ela que o mantém vivo.
    </div>`;

  document.getElementById('modal-rastreador').classList.add('open');
}

async function copiarTexto(txt) {
  try {
    await navigator.clipboard.writeText(txt);
    toast('Endereço copiado', 'success');
  } catch {
    const campo = document.getElementById('rastreador-url');
    if (campo) { campo.select(); document.execCommand('copy'); toast('Endereço copiado', 'success'); }
  }
}

async function carregarTecnicos() {
  const list = document.getElementById('sidebar-list');
  try {
    tecnicos = await api('/tecnicos');
    carregarVisaoGeral(); // não espera — não trava o carregamento da sidebar

    if (tecnicos.length === 0) {
      list.innerHTML = `<div style="padding:20px 14px;color:var(--text-muted);font-size:12px;text-align:center;">Nenhum técnico cadastrado.<br>Clique em + para adicionar.</div>`;
      return;
    }

    list.innerHTML = tecnicos.map(t => `
      <div class="tecnico-section ${tecnicoRecolhido(t.id) ? 'recolhido' : ''}" id="tecnico-section-${t.id}">
        <div class="tecnico-header" style="border-left:3px solid ${escCor(t.cor)}"
             onclick="alternarTecnico(${t.id})" title="Clique para recolher ou abrir">
          <span class="tec-seta">${icone('chevron', 'icone-11')}</span>
          ${avatarTecnico(t)}
          <div class="tecnico-nome" style="color:${escCor(t.cor)}">${esc(t.nome)}${
            (t.ativo === false || t.ativo === 0) ? ' <span class="badge" title="Removido, mas mantido pelo histórico de fichas">inativo</span>' : ''}</div>
          <span class="tec-contagem" id="tec-contagem-${t.id}"></span>
          <div class="tecnico-actions" onclick="event.stopPropagation()">
            <!-- Só o "+", não "+ Ficha": o texto consumia ~45px e empurrava o
                 nome do técnico para as reticências ("JOAO PAUL…"). Nome de
                 pessoa cortado é pior que um rótulo a menos, e os outros três
                 botões da linha já são só ícone — agora os quatro combinam. -->
            <button class="btn-add-ficha" onclick="abrirModalNovaFicha(${t.id})"
                    title="Nova ficha" aria-label="Nova ficha">+</button>
            <button class="btn-link-tecnico btn-carro" onclick="abrirCarro(${t.id}, ${argJs(t.nome)})"
                    title="Peças que este técnico leva no carro" aria-label="Estoque do carro">
              <svg class="icone-svg icone-11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17h14M6 17l-1.5-5.5A2 2 0 0 1 6.4 9h11.2a2 2 0 0 1 1.9 2.5L18 17"/><path d="M7 9V7a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v2"/><circle cx="7.5" cy="17.5" r="1.5"/><circle cx="16.5" cy="17.5" r="1.5"/></svg>
            </button>
            <button class="btn-link-tecnico" onclick="abrirRastreadorTecnico(${t.id})" title="Configurar rastreio de localização">${icone('mapa', 'icone-11')}</button>
            <button class="btn-link-tecnico" onclick="copiarLinkTecnico('${t.token || ''}')" title="Copiar link de acesso do técnico">${icone('externo', 'icone-11')}</button>
            <button class="btn-del-tecnico" onclick="deletarTecnico(event,${t.id})" title="Remover técnico">${icone('x', 'icone-11')}</button>
          </div>
        </div>
        <div class="fichas-do-tecnico" id="fichas-tecnico-${t.id}">
          <div class="loading-row" style="padding:8px 14px;font-size:11px;">Carregando...</div>
        </div>
      </div>
    `).join('');

    await Promise.all(tecnicos.map(t => carregarFichasTecnico(t.id)));
    verificarPontosSemSetor(); // sem await: aviso não pode atrasar a sidebar

  } catch (e) {
    if (list) {
      list.innerHTML = `<div style="padding:20px 14px;color:var(--danger-text);font-size:12px;text-align:center;">${esc(e.message)}</div>`;
    }
    toast('Erro ao carregar técnicos', 'error');
  }
}

async function carregarFichasTecnico(tecnicoId) {
  const container = document.getElementById(`fichas-tecnico-${tecnicoId}`);
  if (!container) return;

  try {
    // Só as rotas em aberto. Depois de concluída a ficha vive no Histórico —
    // a sidebar é a lista de trabalho a fazer, e rota fechada ali só empurra
    // para baixo o que ainda precisa de atenção. Não vira beco sem saída: o
    // Histórico abre a ficha e o botão "Reabrir Rota" continua na tela dela.
    const fichas = await api(`/fichas?tecnico_id=${tecnicoId}&abertas=true`);
    atualizarContagemTecnico(tecnicoId, fichas.length);

    if (fichas.length === 0) {
      container.innerHTML = `<div style="padding:8px 14px;color:var(--text-muted);font-size:11px;">Nenhuma rota em aberto.</div>`;
      return;
    }

    const tecnico = tecnicos.find(t => t.id === tecnicoId);

    container.innerHTML = fichas.map(f => {
      const ativa = fichaAtiva?.id === f.id;
      const concluida = f.status === 'concluida';
      return `
      <!-- "vazia" marca ficha sem atendimento: ela fica mais discreta e mais
           baixa, para o olho encontrar sozinho quem TEM trabalho. Antes uma
           terça com zero atendimentos ocupava o mesmo peso e a mesma altura
           que uma segunda com cinco pontos e 23 km. -->
      <div class="ficha-item ${ativa ? 'active' : ''} ${concluida ? 'ficha-item-concluida' : ''} ${(f.total_servicos || 0) === 0 && !ativa ? 'vazia' : ''}"
           onclick="selecionarFicha(${f.id})"
           id="sidebar-item-${f.id}"
           style="${ativa ? `border-color:${escCor(tecnico?.cor)}` : ''}">
        <button class="btn-del-ficha" onclick="deletarFicha(event,${f.id})">${icone('x', 'icone-11')}</button>
        <div class="ficha-item-dia">
          ${esc(f.dia_semana)}
          ${f.data_referencia === dataDeHoje() ? '<span class="tag-hoje">hoje</span>' : ''}
          ${concluida ? `<span class="mini-check" title="Concluída">${icone('concluir', 'icone-10')}</span>` : ''}
        </div>
        <div class="ficha-item-meta">
          ${f.data_referencia ? `<span>${esc(formatarData(f.data_referencia))}</span>` : ''}
          <span class="badge ${f.total_servicos > 0 ? 'accent' : ''}">${f.total_servicos} atendimento${f.total_servicos !== 1 ? 's' : ''}</span>
          ${f.distancia_total > 0 ? `<span class="badge">${fmtKm(f.distancia_total)} km</span>` : ''}
        </div>
      </div>`;
    }).join('');

  } catch (e) {
    container.innerHTML = `<div style="padding:8px 14px;color:var(--danger-text);font-size:11px;">Falha ao carregar fichas.</div>`;
    console.error('Erro ao carregar fichas do técnico', tecnicoId, e);
  }
}

// Painel de visão geral — some assim que uma ficha é aberta (é a tela de
// "nenhuma ficha selecionada"), então isso é o que a equipe vê ao abrir
// o sistema: quanto está rodando, sem precisar clicar em nada.
async function carregarVisaoGeral() {
  const painel = document.getElementById('visao-geral');
  if (!painel) return;

  try {
    const fichas = await api('/fichas');
    const fichasAtivas = fichas.filter(f => f.status !== 'concluida');

    const totalRotas  = fichasAtivas.length;
    const totalPontos = fichasAtivas.reduce((soma, f) => soma + (f.total_servicos || 0), 0);
    const totalKm     = fichasAtivas.reduce((soma, f) => soma + (f.distancia_total || 0), 0);

    animarNumero(document.getElementById('vg-tecnicos'), tecnicos.length);
    animarNumero(document.getElementById('vg-rotas'), totalRotas);
    animarNumero(document.getElementById('vg-pontos'), totalPontos);
    animarNumero(document.getElementById('vg-km'), totalKm, {
      formatar: v => v.toFixed(1).replace('.', ','),
    });

    const porTecnico = new Map();
    fichasAtivas.forEach(f => {
      const atual = porTecnico.get(f.tecnico_id) || {
        nome: f.tecnico_nome, cor: f.tecnico_cor, rotas: 0, pontos: 0, km: 0,
      };
      atual.rotas  += 1;
      atual.pontos += f.total_servicos || 0;
      atual.km     += f.distancia_total || 0;
      porTecnico.set(f.tecnico_id, atual);
    });

    const listaEl = document.getElementById('visao-geral-tecnicos');
    if (listaEl) {
      listaEl.innerHTML = Array.from(porTecnico.values())
        .sort((a, b) => b.km - a.km)
        .map(t => `
          <div class="vg-tecnico-row">
            <span class="vg-tecnico-dot" style="background:${escCor(t.cor)}"></span>
            <span class="vg-tecnico-nome">${esc(t.nome)}</span>
            <span class="vg-tecnico-meta">${t.rotas} rota${t.rotas !== 1 ? 's' : ''} · ${t.pontos} pt${t.pontos !== 1 ? 's' : ''} · ${fmtKm(t.km)} km</span>
          </div>`)
        .join('');
    }
  } catch (e) {
    console.error('Erro ao carregar visão geral', e);
  }

  carregarResumoSetores();
}

// Quanto cada frente (Panasonic / Philco / Loja) representa. Sem isso, tudo
// vira um número só e não dá pra saber de onde vem o trabalho.
async function carregarResumoSetores() {
  const alvo = document.getElementById('vg-setores');
  if (!alvo) return;

  try {
    const r = await api('/setores/resumo');
    const lista = (r.setores || []).filter(s => s.pontos > 0);
    const semSetor = r.sem_setor || 0;
    if (lista.length === 0 && semSetor === 0) { alvo.innerHTML = ''; return; }

    // O denominador é o total de pontos em aberto, NÃO a soma dos já
    // classificados. Dividindo pelos classificados, um único setor preenchido
    // sempre daria 100% — foi o que aconteceu: Panasonic marcava 100% do
    // painel sendo 5 de 44 pontos.
    const total = r.total || lista.reduce((soma, s) => soma + s.pontos, 0);
    const pctDe = (n) => (total ? Math.round((n / total) * 100) : 0);

    const linhaSemSetor = semSetor > 0 ? `
        <div class="vg-setor-row vg-setor-row--sem" onclick="abrirClassificacaoEmLote()"
             title="Clique para classificar estes atendimentos">
          <span class="vg-tecnico-dot" style="background:var(--text-muted)"></span>
          <span class="vg-tecnico-nome" style="color:var(--text-muted)">Sem setor</span>
          <div class="vg-setor-barra">
            <div class="vg-setor-preenchido" style="width:${pctDe(semSetor)}%;background:var(--text-muted)"></div>
          </div>
          <span class="vg-tecnico-meta">${semSetor} pt${semSetor !== 1 ? 's' : ''} · ${pctDe(semSetor)}%</span>
        </div>` : '';

    alvo.innerHTML = `
      <div class="vg-setores-titulo">Por setor <span class="vg-setores-escopo">em aberto · ${total} pt${total !== 1 ? 's' : ''}</span></div>
      ${lista.map(s => `
        <div class="vg-setor-row">
          <span class="vg-tecnico-dot" style="background:${escCor(s.cor)}"></span>
          <span class="vg-tecnico-nome">${esc(s.nome)}</span>
          <div class="vg-setor-barra">
            <div class="vg-setor-preenchido" style="width:${pctDe(s.pontos)}%;background:${escCor(s.cor)}"></div>
          </div>
          <span class="vg-tecnico-meta">${s.pontos} pt${s.pontos !== 1 ? 's' : ''} · ${pctDe(s.pontos)}%</span>
        </div>`).join('')}
      ${linhaSemSetor}
    `;
  } catch (e) {
    alvo.innerHTML = '';
  }
}

// Período selecionado no Histórico. Vazio = tudo, que é o padrão.
let historicoDias = '';

function iniciarFiltroHistorico() {
  const barra = document.getElementById('hist-periodo');
  if (!barra) return;

  barra.querySelectorAll('.hist-periodo-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      historicoDias = btn.dataset.dias || '';
      barra.querySelectorAll('.hist-periodo-btn')
           .forEach(b => b.classList.toggle('active', b === btn));
      carregarHistorico();
      // A tendência não entra aqui: ela tem janela própria de 8 semanas
      // (/metricas/tendencia) e não responde a este filtro. Recarregá-la
      // seria só gastar rede para redesenhar exatamente a mesma coisa.
    });
  });
}

async function carregarHistorico() {
  const statsEl = document.getElementById('historico-stats');
  const listaEl = document.getElementById('historico-lista');
  if (!statsEl || !listaEl) return;

  try {
    // Filtro de período. "Tudo" continua sendo o padrão para não mudar o que
    // o usuário via antes sem ele pedir — os recortes são um atalho, não uma
    // troca do comportamento.
    const consulta = historicoDias
      ? `/fichas?status=concluida&dias=${historicoDias}`
      : '/fichas?status=concluida';
    const fichas = await api(consulta);

    const totalRotas  = fichas.length;
    const totalPontos = fichas.reduce((soma, f) => soma + (f.total_servicos || 0), 0);
    const totalKm     = fichas.reduce((soma, f) => soma + (f.distancia_total || 0), 0);

    statsEl.innerHTML = `
      <div class="vg-stat">
        <div class="vg-valor">${totalRotas}</div>
        <div class="vg-label">Rota${totalRotas !== 1 ? 's' : ''} Concluída${totalRotas !== 1 ? 's' : ''}</div>
      </div>
      <div class="vg-stat">
        <div class="vg-valor">${totalPontos}</div>
        <div class="vg-label">Atendimento${totalPontos !== 1 ? 's' : ''} Atendido${totalPontos !== 1 ? 's' : ''}</div>
      </div>
      <div class="vg-stat">
        <div class="vg-valor">${fmtKm(totalKm)}</div>
        <div class="vg-label">Km Rodados</div>
      </div>
    `;

    if (fichas.length === 0) {
      listaEl.innerHTML = `
        <div class="historico-vazio">
          ${icone('historico', 'icone-24')}
          <p>Nenhuma rota concluída ainda.</p>
        </div>`;
      return;
    }

    const ordenadas = [...fichas].sort((a, b) => new Date(b.concluida_em || 0) - new Date(a.concluida_em || 0));

    listaEl.innerHTML = ordenadas.map(f => `
      <div class="historico-item" onclick="selecionarFichaHistorico(${f.id})">
        <span class="vg-tecnico-dot" style="background:${escCor(f.tecnico_cor)}"></span>
        <div class="historico-item-info">
          <div class="historico-item-titulo">${esc(f.dia_semana)} <span class="historico-item-tecnico">· ${esc(f.tecnico_nome || '')}</span></div>
          <div class="historico-item-meta">
            ${f.concluida_em ? `<span>${icone('calendario', 'icone-11')} ${formatarDataHora(f.concluida_em)}</span>` : ''}
            <span>${f.total_servicos} atendimento${f.total_servicos !== 1 ? 's' : ''}</span>
            <span>${fmtKm(f.distancia_total)} km</span>
            ${f.conciliada_em ? `<span class="conc-tag ok" style="font-size:8px;padding:2px 6px;">planilha ok</span>` : ''}
          </div>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); alternarStatusFicha(${f.id}, 'concluida')">
          ${icone('atualizar', 'icone-12')} Reabrir
        </button>
      </div>
    `).join('');
  } catch (e) {
    listaEl.innerHTML = `<div class="historico-vazio"><p>Falha ao carregar histórico.</p></div>`;
    console.error('Erro ao carregar histórico', e);
  }

  carregarTendencia();
}

function selecionarFichaHistorico(fichaId) {
  switchMainTab('roteiros');
  selecionarFicha(fichaId);
}

async function carregarTendencia() {
  const wrap = document.getElementById('tendencia-wrap');
  const lista = document.getElementById('tendencia-lista');
  if (!wrap || !lista) return;

  try {
    const { semanas } = await api('/metricas/tendencia');
    if (!semanas || semanas.length === 0) { wrap.style.display = 'none'; return; }

    wrap.style.display = '';
    lista.innerHTML = [...semanas].reverse().map(s => `
      <div class="tendencia-semana">
        <div class="tendencia-semana-titulo">${esc(s.semana)}</div>
        <div class="tendencia-tecnicos">
          ${s.tecnicos.map(t => `
            <div class="vg-tecnico-row">
              <span class="vg-tecnico-dot" style="background:${escCor(t.tecnico_cor)}"></span>
              <span class="vg-tecnico-nome">${esc(t.tecnico_nome)}</span>
              <span class="vg-tecnico-meta">${t.rotas} rota${t.rotas !== 1 ? 's' : ''} · ${t.pontos} pt${t.pontos !== 1 ? 's' : ''} · ${fmtKm(t.km)} km</span>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  } catch (e) {
    wrap.style.display = 'none';
    console.error('Erro ao carregar tendência', e);
  }
}

function exportarHistorico() {
  // O XLSX segue o período que está na tela. Exportar "tudo" enquanto o
  // usuário olha os últimos 7 dias entregaria uma planilha que não confere
  // com o que ele acabou de ver — e ele levaria isso para uma reunião.
  const url = historicoDias
    ? `/api/historico/exportar?dias=${historicoDias}`
    : '/api/historico/exportar';
  window.open(url, '_blank');
}

// ─── Peças compradas (planilha de pedidos) ──────────────────────────
// Vincular a peça ao cliente aqui, escolhendo da lista, faz o nome gravado
// ficar idêntico ao do site — e aí a baixa ao concluir a rota casa exato.
let clientesConhecidos = [];

// ─── Cadastrar cliente na hora, direto da linha da peça ─────────────
// A sugestão da lista (datalist acima) só sabe quem já apareceu num roteiro
// de técnico — mas quem comprou a peça pode nunca ter tido atendimento
// nenhum ainda. Sem isso, a única saída era digitar um nome solto no campo
// (que grava na planilha, mas não vira cliente de verdade em lugar nenhum).
let _clienteRapidoLinha = null;

function abrirClienteRapido(linha) {
  _clienteRapidoLinha = linha;
  document.getElementById('cliente-rapido-nome').value =
    document.getElementById(`peca-cliente-${linha}`)?.value.trim() || '';
  document.getElementById('cliente-rapido-telefone').value = '';
  document.getElementById('modal-cliente-rapido').classList.add('open');
  setTimeout(() => document.getElementById('cliente-rapido-nome').focus(), 80);
}

async function salvarClienteRapido() {
  const nome = document.getElementById('cliente-rapido-nome').value.trim();
  if (!nome) { toast('Informe o nome do cliente', 'error'); return; }
  const telefone = document.getElementById('cliente-rapido-telefone').value.trim();

  const btn = document.getElementById('cliente-rapido-salvar');
  btn.disabled = true;
  btn.textContent = 'Cadastrando...';

  try {
    await api('/pedidos/clientes', { method: 'POST', body: JSON.stringify({ nome, telefone }) });
    toast(`${nome} cadastrado`, 'success');

    // Some pra lista de sugestão na hora, sem precisar recarregar a aba.
    if (!clientesConhecidos.some(c => c.nome === nome)) {
      clientesConhecidos.push({ nome, aparelho: '', modelo: '' });
      const datalist = document.getElementById('lista-clientes');
      if (datalist) datalist.insertAdjacentHTML('beforeend', `<option value="${esc(nome)}"></option>`);
    }

    const campo = document.getElementById(`peca-cliente-${_clienteRapidoLinha}`);
    if (campo) {
      campo.value = nome;
      campo.dispatchEvent(new Event('change')); // grava na planilha (salvarPecaInline)
    }
    fecharModais();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Cadastrar';
  }
}

async function carregarPecas() {
  const lista = document.getElementById('pecas-lista');
  if (!lista) return;

  const todas = document.getElementById('pecas-mostrar-todas')?.checked;
  lista.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:30px;"><div class="spinner"></div> Lendo a planilha...</div>`;

  let r;
  try {
    r = await api(`/pedidos${todas ? '?todos=true' : ''}`);
  } catch (e) {
    lista.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  clientesConhecidos = r.clientes || [];
  const pedidos = r.pedidos || [];

  if (pedidos.length === 0) {
    lista.innerHTML = `
      <div class="historico-vazio">
        ${icone('check', 'icone-24')}
        <p>${todas ? 'Nenhuma compra na planilha.' : 'Todas as peças já estão vinculadas a um cliente.'}</p>
      </div>`;
    return;
  }

  // Contagem por estágio: é o que responde "cadê a peça do fulano?" antes
  // mesmo de procurar. Antes o status_compra vinha da planilha até o
  // navegador e era descartado na hora de desenhar.
  const porEstagio = { chegou: 0, ENVIADO: 0, FATURADO: 0, APROVADO: 0, CRIADO: 0 };
  pedidos.forEach(p => {
    if (p.chegou_em) porEstagio.chegou++;
    else porEstagio[(p.status_compra || 'CRIADO').toUpperCase()] =
      (porEstagio[(p.status_compra || 'CRIADO').toUpperCase()] || 0) + 1;
  });

  lista.innerHTML = `
    <div class="pecas-filtros" id="pecas-filtros">
      ${[['', 'Todas', pedidos.length],
         ['chegou', 'Chegou', porEstagio.chegou],
         ['ENVIADO', 'A caminho', porEstagio.ENVIADO],
         ['FATURADO', 'Faturada', porEstagio.FATURADO],
         ['pendente', 'Sem cliente', pedidos.filter(p => !p.cliente_final).length]]
        .map(([v, rot, n]) => `
          <button class="pecas-filtro${v === '' ? ' ativo' : ''}" data-estagio="${v}"
                  onclick="filtrarPorEstagio('${v}')">
            ${rot} <span class="pecas-filtro-n">${n}</span>
          </button>`).join('')}
    </div>
    <div class="pecas-barra">
      <input class="pecas-busca" id="pecas-busca" type="search" autocomplete="off"
             placeholder="Filtrar por peça, cliente ou pedido..."
             oninput="filtrarPecas(this.value)">
      <span class="pecas-contagem" id="pecas-contagem">${pedidos.length} compra${pedidos.length !== 1 ? 's' : ''}</span>
      ${r.sugestao_peca_ativa
        ? `<span class="conc-tag ok" title="O código/descrição da peça é lido sozinho da nota fiscal (XML) que a Panasonic envia por e-mail — só preencha à mão se vier em branco">campo "Peça" preenche sozinho</span>`
        : `<span class="conc-tag neutro" title="Leitura automática da nota fiscal desligada neste ambiente — preencha o campo Peça à mão">campo "Peça" é preenchido à mão</span>`}
      <button class="btn btn-ghost btn-sm" onclick="revisarAmarelas()"
              title="Compras que a planilha vinculou a um cliente só pelo nome (sem confirmar pelo número da OS ou modelo) — vale conferir se não casou errado">Conferir vínculos incertos</button>
    </div>
    <div id="pecas-revisao"></div>
  ` + pedidos.map(p => `
    <div class="peca-linha${p.cliente_final ? ' tem-cliente' : ''}${p.chegou_em ? ' chegou' : ''}"
         id="peca-${p.linha}" data-linha="${p.linha}"
         data-chave="${esc(p.chave || '')}"
         data-valor="${esc(p.valor || '')}"
         data-nota="${esc(p.nota_fiscal || '')}"
         data-estagio="${p.chegou_em ? 'chegou' : esc((p.status_compra || 'CRIADO').toUpperCase())}"
         data-pendente="${p.cliente_final ? '0' : '1'}"
         data-busca="${esc(((p.peca || '') + ' ' + (p.cliente_final || '') + ' ' + (p.pedido || '') + ' ' + (p.nota_fiscal || '')).toLowerCase())}">

      <div class="peca-ident">
        <span class="peca-valor">${esc(formatarValorPeca(p.valor))}</span>
        <span class="peca-meta">${p.nota_fiscal
            ? 'NF ' + esc(p.nota_fiscal.slice(-8))
            : (p.pedido ? 'Pedido ' + esc(p.pedido) : 'sem nota ainda')}
          · ${esc((p.data || '').split(' ')[0])}</span>
        ${estagioPeca(p)}
        <span class="peca-estoque" id="peca-estoque-${p.linha}"></span>
      </div>

      <div class="peca-campo">
        <label class="peca-rot" for="peca-desc-${p.linha}">Peça</label>
        <input class="form-input peca-input" id="peca-desc-${p.linha}"
               value="${esc(p.peca)}" title="${esc(p.peca)}"
               placeholder="Ex: NR-BB64PV1BA"
               onchange="salvarPecaInline(${p.linha})">
      </div>

      <div class="peca-campo">
        <label class="peca-rot" for="peca-cliente-${p.linha}">Cliente</label>
        <div class="peca-cliente-linha">
          <input class="form-input peca-input" list="lista-clientes"
                 id="peca-cliente-${p.linha}" value="${esc(p.cliente_final)}"
                 placeholder="Escolha ou digite..."
                 onchange="salvarPecaInline(${p.linha})">
          <!-- A lista sugere quem já apareceu num roteiro de técnico, mas o
               dono da peça nem sempre é essa pessoa (pode ser cliente de
               balcão, de outra marca, sem atendimento nenhum ainda) — daqui
               cadastra de verdade em vez de só digitar um nome solto. -->
          <button type="button" class="peca-cliente-add" title="Cadastrar um cliente novo"
                  onclick="abrirClienteRapido(${p.linha})">+</button>
        </div>
      </div>

      <!-- Estado da gravação. Fica NA LINHA, e não num toast, porque o toast
           some e some sozinho: quem preencheu cinco linhas seguidas precisa
           poder olhar para trás e ver quais já foram para a planilha. -->
      <div class="peca-acoes">
        <span class="peca-estado" id="peca-estado-${p.linha}">${
          p.cliente_final ? '<span class="ok">✓ na planilha</span>' : ''}</span>
        <button class="peca-chegou${p.chegou_em ? ' marcado' : ''}"
                id="peca-chegou-${p.linha}"
                title="${p.chegou_em ? 'Chegou em ' + esc(p.chegou_em) + ' — clique para desfazer'
                                     : 'Marcar que a peça chegou na oficina'}"
                onclick="alternarChegada(${p.linha})">
          ${p.chegou_em ? '📦 chegou' : 'marcar chegada'}
        </button>
        <button class="peca-estoque-btn" id="peca-estoque-btn-${p.linha}"
                title="Opcional: soma essa peça ao saldo da aba Estoque, já com o custo desta nota preenchido. Vincular ao cliente (acima) NÃO faz isso sozinho."
                onclick="darEntradaEstoqueDaPeca(${p.linha})">
          Registrar no estoque
        </button>
        ${botaoAgendarPeca(p)}
      </div>

      ${sugestaoDeCliente(p)}
      <div class="peca-sugestao-slot" id="sugestao-${p.linha}"
           data-nota="${esc(p.nota_fiscal)}"></div>
    </div>
  `).join('') + `
    <datalist id="lista-clientes">
      ${clientesConhecidos.map(c => `<option value="${esc(c.nome)}">${esc(c.aparelho)}${c.modelo ? ' · ' + esc(c.modelo) : ''}</option>`).join('')}
    </datalist>`;

  atualizarSeloPecas(r.pendentes ?? pedidos.filter(p => !p.cliente_final).length);

  // Mostra o saldo do estoque ao lado de cada compra (o elo com a aba Estoque).
  anotarSaldosEstoque(pedidos);

  // Sugestões vêm depois, sem travar a tela (ler os XMLs das notas é lento).
  if (r.sugestao_peca_ativa) buscarSugestoesPecas(pedidos);

  // Escolheu um cliente que o site conhece? já sugere o modelo dele.
  pedidos.forEach(p => {
    const inp = document.getElementById(`peca-cliente-${p.linha}`);
    inp?.addEventListener('change', () => {
      const achado = clientesConhecidos.find(c => c.nome === inp.value);
      const campoPeca = document.getElementById(`peca-desc-${p.linha}`);
      if (achado?.modelo && campoPeca && !campoPeca.value.trim()) {
        campoPeca.value = achado.modelo;
      }
    });
  });
}

// Anota "em estoque: N" em cada compra, cruzando o código da peça (o texto do
// campo Peça, ex NR-BB64PV1BA) com os saldos do estoque. Best-effort: só marca
// o que casa exato; peça que não está no estoque simplesmente não recebe selo.
async function anotarSaldosEstoque(pedidos) {
  const codigos = [...new Set(pedidos
    .map(p => (document.getElementById(`peca-desc-${p.linha}`)?.value || p.peca || '').trim().toUpperCase())
    .filter(Boolean))];
  if (!codigos.length) return;
  let saldos;
  try {
    const d = await api('/estoque/saldos?codigos=' + encodeURIComponent(codigos.join(',')));
    saldos = d.saldos || {};
  } catch { return; }
  pedidos.forEach(p => {
    const cod = (document.getElementById(`peca-desc-${p.linha}`)?.value || p.peca || '').trim().toUpperCase();
    const slot = document.getElementById(`peca-estoque-${p.linha}`);
    if (!slot) return;
    const info = saldos[cod];
    slot.innerHTML = info
      ? `<span class="peca-estoque-tag" title="Saldo atual no estoque">em estoque: ${info.saldo.toLocaleString('pt-BR', { maximumFractionDigits: 3 })}</span>`
      : '';
  });
}

// Garante que a lista de prateleiras esteja carregada antes de abrir o modal
// de entrada a partir da aba Peças (onde a aba Estoque pode nunca ter sido aberta).
async function _garantirGruposCarregados() {
  if (estoqueGrupos.length) return;
  try { estoqueGrupos = (await api('/estoque/grupos')).grupos || []; } catch { /* segue sem prateleira */ }
}

// Dá entrada da peça comprada no estoque, reaproveitando o modal de entrada já
// testado — mas carimbado com a nota (origem 'nota', idempotente). Assim o
// senhor confere quantidade, custo e a prateleira antes de confirmar.
async function darEntradaEstoqueDaPeca(linha) {
  const linhaEl = document.getElementById(`peca-${linha}`);
  const codigo = (document.getElementById(`peca-desc-${linha}`)?.value || '').trim();
  if (!codigo) { toast('Preencha o código/modelo da peça antes de mandar ao estoque.', 'error'); return; }
  // O valor da planilha vem "R$ 123,45" ou "123.45" — normaliza para número.
  const valorBruto = String(linhaEl?.dataset.valor || '');
  const custo = parseFloat(valorBruto.replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.')) || 0;
  const nota = (linhaEl?.dataset.nota || '').trim();

  await _garantirGruposCarregados();
  estoqueMovModo = 'entrada';
  _limparCamposEstoque();
  document.getElementById('estoque-mov-titulo').textContent = `Entrada no estoque — ${codigo}`;
  document.getElementById('estoque-mov-codigo-fixo').value = '';
  document.getElementById('estoque-mov-referencia').value = nota; // marca a nota
  document.getElementById('estoque-mov-codigo').value = codigo;
  document.getElementById('estoque-mov-desc').value = codigo;
  document.getElementById('estoque-mov-qtd').value = 1;
  document.getElementById('estoque-mov-custo').value = custo || '';
  _popularSelectEstoque('');
  _visibilidadeModalEstoque({ codigo: true, desc: true, estoque: true, categoria: true, modelo: true, qtdcusto: true, custo: true, obs: true });
  _labelQtd('Quantidade');
  document.getElementById('modal-estoque-mov').classList.add('open');
  setTimeout(() => document.getElementById('estoque-mov-qtd').select(), 80);
}

// Botão "Agendar cliente": manda o cliente desta compra pra fila de Agendar
// Clientes (aba própria). Só faz sentido depois que a peça chegou — por isso
// fica escondido por CSS (.peca-linha:not(.chegou) .peca-agendar) enquanto o
// estágio não é "chegou", e some sozinho quando alternarChegada() alterna
// essa classe na linha, sem precisar recarregar a lista inteira.
function botaoAgendarPeca(p) {
  if (p.agendamento_os_id) {
    return `
      <button class="peca-agendar enviado" onclick="abrirOSDetalhe(${p.agendamento_os_id})"
              title="Já está na fila de Agendar Clientes — clique pra abrir a OS">
        ✓ enviado p/ agendar
      </button>`;
  }
  return `
    <button class="peca-agendar" id="peca-agendar-${p.linha}"
            title="Manda este cliente pra fila de Agendar Clientes, pra marcar a visita de instalação/revisita"
            onclick="enviarParaAgendar(${p.linha})">
      Agendar cliente
    </button>`;
}

async function enviarParaAgendar(linha) {
  const linhaEl = document.getElementById(`peca-${linha}`);
  const cliente = document.getElementById(`peca-cliente-${linha}`)?.value.trim();
  const peca = document.getElementById(`peca-desc-${linha}`)?.value.trim() || '';
  if (!cliente) {
    toast('Preencha o cliente antes de mandar pra Agendar Clientes.', 'error');
    return;
  }
  const btn = document.getElementById(`peca-agendar-${linha}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Enviando...'; }

  try {
    const r = await api(`/pedidos/${linha}/agendar-cliente`, {
      method: 'POST',
      body: JSON.stringify({ chave: linhaEl?.dataset.chave, cliente, peca }),
    });
    toast(r.mensagem, 'success');
    if (btn) {
      btn.outerHTML = `
        <button class="peca-agendar enviado" onclick="abrirOSDetalhe(${r.id})">
          ✓ enviado p/ agendar
        </button>`;
    }
    carregarSeloAgendar();
  } catch (e) {
    toast(e.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Agendar cliente'; }
  }
}

// Busca as peças no XML das notas fiscais e injeta nos cards já renderizados.
// Em blocos pequenos, pra as primeiras sugestões aparecerem rápido em vez de
// tudo de uma vez no fim.
async function buscarSugestoesPecas(pedidos) {
  const alvos = pedidos.filter(p => !p.peca && p.nota_fiscal);
  if (alvos.length === 0) return;

  const aviso = document.querySelector('.pecas-barra .conc-tag.ok');
  if (aviso) aviso.textContent = 'lendo notas fiscais...';

  const TAMANHO = 6;
  let achadas = 0;

  for (let i = 0; i < alvos.length; i += TAMANHO) {
    const bloco = alvos.slice(i, i + TAMANHO);
    let r;
    try {
      r = await api(`/pedidos/sugestoes?notas=${bloco.map(p => p.nota_fiscal).join(',')}`);
    } catch (e) {
      console.warn('sugestão de peça falhou:', e.message);
      break;
    }

    Object.entries(r.sugestoes || {}).forEach(([nota, resumo]) => {
      const alvo = alvos.find(p => p.nota_fiscal === nota);
      if (!alvo || !resumo) return;
      const slot = document.getElementById(`sugestao-${alvo.linha}`);
      const campo = document.getElementById(`peca-desc-${alvo.linha}`);
      if (!slot || !campo) return;

      achadas++;
      campo.dataset.sugestao = resumo;
      if (!campo.value.trim()) campo.value = resumo;
      slot.innerHTML = `
        <div class="peca-sugestao">
          <div class="peca-sugestao-txt"><strong>Da nota fiscal:</strong> ${esc(resumo)}</div>
        </div>`;
    });
  }

  if (aviso) {
    aviso.textContent = achadas
      ? `${achadas} peça(s) lidas da nota`
      : 'peça automática ligada';
  }
}

// Baixas que casaram só pelo nome (amarelas na planilha). É o elo mais fraco
// do casamento, então dá pra conferir e desfazer o que ficou errado.
async function revisarAmarelas() {
  const alvo = document.getElementById('pecas-revisao');
  if (!alvo) return;
  alvo.innerHTML = `<div class="loading-row" style="display:flex;gap:8px;padding:14px;"><div class="spinner"></div> Conferindo...</div>`;

  let r;
  try {
    r = await api('/pedidos/revisar');
  } catch (e) {
    alvo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const itens = r.itens || [];
  if (itens.length === 0) {
    alvo.innerHTML = `<div class="conc-alerta" style="margin:0 0 14px;">
      Nenhuma baixa duvidosa. Todas casaram por nº da OS ou nome + modelo.
    </div>`;
    return;
  }

  alvo.innerHTML = `
    <div class="conc-titulo">Baixas que casaram só pelo nome (${itens.length})</div>
    ${itens.map(i => `
      <div class="conc-item" id="revisao-${i.linha}">
        <span class="conc-tag aviso">conferir</span>
        <div style="flex:1;min-width:0;">
          <div class="conc-cliente">${esc(i.cliente)}</div>
          <div class="conc-meta">linha ${i.linha} · ${esc(i.valor)} · ${esc(i.peca) || 'sem peça'}</div>
          <button class="btn btn-ghost btn-sm" style="margin-top:7px;"
                  onclick="desfazerBaixa(${i.linha})">Desfazer baixa</button>
        </div>
      </div>`).join('')}
  `;
}

async function desfazerBaixa(linha) {
  if (!confirm(`Desfazer a baixa da linha ${linha}?`)) return;
  try {
    await api(`/pedidos/${linha}/desfazer`, { method: 'PUT' });
    toast('Baixa desfeita', 'success');
    document.getElementById(`revisao-${linha}`)?.remove();
    carregarSeloPecas();
  } catch (e) { toast(e.message, 'error'); }
}

// Selo com quantas peças estão esperando vínculo — sem isso ninguém lembra
// de abrir a aba, e a baixa simplesmente não acontece no dia seguinte.
function atualizarSeloPecas(qtd) {
  const aba = document.getElementById('mtab-pecas');
  if (!aba) return;
  aba.querySelector('.aba-selo')?.remove();
  if (qtd > 0) {
    const selo = document.createElement('span');
    selo.className = 'aba-selo';
    selo.textContent = qtd;
    selo.title = `${qtd} peça(s) sem cliente vinculado`;
    aba.appendChild(selo);
  }
}

async function carregarSeloPecas() {
  try {
    const r = await api('/pedidos/pendentes');
    if (r.configurada) atualizarSeloPecas(r.pendentes);
  } catch (e) { /* integração desligada: sem selo, sem barulho */ }
}

// ─── Peças: gravar direto, sem botão ────────────────────────────────
//
// O pedido era: digitar o nome do cliente e a planilha já atualizar. Antes
// era preciso preencher e AINDA clicar "Vincular" — duas ações para uma
// intenção, e quem preenchia várias linhas seguidas esquecia o clique e
// perdia o trabalho ao trocar de aba.
//
// Grava ao sair do campo (onchange), não a cada tecla: salvar por
// caractere geraria dezenas de escritas na planilha por nome digitado, e a
// API do Sheets tem cota por minuto.
//
// E NÃO recarrega a lista depois de gravar. Recarregar tiraria a linha de
// baixo do cursor e jogaria fora a rolagem — exatamente o defeito que o
// auto-refresh tinha. A linha se atualiza sozinha, no lugar.
const _pecaUltimoValor = {};

async function salvarPecaInline(linha) {
  const campoCliente = document.getElementById(`peca-cliente-${linha}`);
  const campoPeca = document.getElementById(`peca-desc-${linha}`);
  const estado = document.getElementById(`peca-estado-${linha}`);
  if (!campoCliente || !campoPeca || !estado) return;

  const cliente = campoCliente.value.trim();
  const peca = campoPeca.value.trim();

  // Sem cliente não há o que vincular; peça sozinha ainda não é um vínculo.
  if (!cliente) return;

  // Não regrava o que já está igual: sair e voltar num campo sem alterar
  // nada não deve custar uma escrita na planilha.
  const assinatura = `${cliente}|${peca}`;
  if (_pecaUltimoValor[linha] === assinatura) return;

  estado.innerHTML = '<span class="salvando">gravando...</span>';
  try {
    const r = await api(`/pedidos/${linha}`, {
      method: 'PUT',
      body: JSON.stringify({ cliente, peca }),
    });
    _pecaUltimoValor[linha] = assinatura;
    estado.innerHTML = '<span class="ok">✓ na planilha</span>';
    document.getElementById(`peca-${linha}`)?.classList.add('tem-cliente');
    campoPeca.title = peca;
    carregarSeloPecas();
    tratarRetornoAgoraOS(linha, cliente, peca, r.agoraos);
  } catch (e) {
    estado.innerHTML = `<span class="falhou" title="${esc(e.message)}">✕ não gravou</span>`;
    toast(e.message, 'error');
  }
}

// ─── Fotos da etiqueta ──────────────────────────────────────────────
//
// Carregadas DEPOIS da lista, por atendimento: cada foto é uma imagem em
// base64, e trazê-las junto do roteiro deixaria pesada toda abertura de
// rota para um dado que se olha de um ponto por vez.
async function carregarFotosDoRoteiro(servicoIds) {
  for (const id of servicoIds) {
    try {
      const r = await api(`/servicos/${id}/fotos`);
      const slot = document.getElementById(`fotos-${id}`);
      if (!slot || !(r.fotos || []).length) continue;
      slot.innerHTML = r.fotos.map(f => `
        <img class="roteiro-foto" src="${f.foto}" loading="lazy"
             alt="Etiqueta enviada pelo técnico"
             title="${esc(f.legenda || 'foto')} · ${esc(f.criado_em || '')}"
             onclick="ampliarFoto(this.src)">`).join('');
    } catch { /* foto é apoio: falhar aqui não pode atrapalhar a rota */ }
  }
}

// Clique amplia. É lendo o número de série ampliado que se pede a peça —
// miniatura de 62px não serve para isso.
function ampliarFoto(src) {
  const lupa = document.createElement('div');
  lupa.className = 'lupa-fundo';
  lupa.innerHTML = `<img src="${src}" alt="Etiqueta ampliada">
                    <div class="lupa-dica">clique para fechar</div>`;
  lupa.onclick = () => lupa.remove();
  document.addEventListener('keydown', function fechar(ev) {
    if (ev.key === 'Escape') { lupa.remove(); document.removeEventListener('keydown', fechar); }
  });
  document.body.appendChild(lupa);
}

// ─── Desfecho do atendimento (visto do escritório) ──────────────────
//
// O técnico registra em campo o que aconteceu; sem mostrar aqui, o dado
// ficaria preso no aplicativo dele. "Precisa de peça" é o que mais importa:
// é o atendimento que vai exigir uma segunda visita.
const DESFECHO_ROTULO = {
  resolvido:    { txt: 'Resolvido',       classe: 'df-resolvido' },
  precisa_peca: { txt: 'Precisa de peça', classe: 'df-precisa-peca' },
  cotacao_peca: { txt: 'Cotação de peça', classe: 'df-cotacao-peca' },
  volto_depois: { txt: 'Volta depois',    classe: 'df-volto' },
  nao_atendido: { txt: 'Reagendar',        classe: 'df-nao-atendido' },
};

function seloDesfecho(s) {
  const d = DESFECHO_ROTULO[s.desfecho];
  if (!d) return '';
  const extra = s.desfecho_peca || s.desfecho_motivo || '';
  return `<div class="roteiro-desfecho ${d.classe}">${d.txt}${
    extra ? ' · ' + esc(extra) : ''}</div>${
    s.desfecho_obs ? `<div class="roteiro-obs">${esc(s.desfecho_obs)}</div>` : ''}`;
}

// ─── Estágio da compra ──────────────────────────────────────────────
//
// A Panasonic informa quatro estados por e-mail, e o robô os grava na
// planilha: pedido criado, pagamento aprovado, nota faturada, produto
// enviado. Tudo isso chegava até o navegador e era jogado fora na hora de
// desenhar — a tela só sabia dizer "sem cliente".
//
// É a informação que a operação mais usa: quem vai reagendar a visita
// precisa saber se a peça saiu, não se a compra foi registrada.
const ESTAGIOS = {
  CRIADO:   { rotulo: 'aguardando pagamento', classe: 'e-criado' },
  APROVADO: { rotulo: 'pago',                 classe: 'e-aprovado' },
  FATURADO: { rotulo: 'nota emitida',         classe: 'e-faturado' },
  ENVIADO:  { rotulo: 'a caminho',            classe: 'e-enviado' },
};

function estagioPeca(p) {
  if (p.chegou_em) {
    return `<span class="peca-estagio e-chegou" title="Registrado em ${esc(p.chegou_em)}">chegou</span>`;
  }
  const e = ESTAGIOS[(p.status_compra || '').toUpperCase()] || ESTAGIOS.CRIADO;
  return `<span class="peca-estagio ${e.classe}">${e.rotulo}</span>`;
}

// Registra que a peça chegou na bancada. É o elo que faltava: a planilha
// acompanha até "enviado", e entre o envio e a caixa aberta passam dias que
// não existiam em lugar nenhum.
async function alternarChegada(linha) {
  const el = document.getElementById(`peca-${linha}`);
  const btn = document.getElementById(`peca-chegou-${linha}`);
  if (!el || !btn) return;

  const marcando = !btn.classList.contains('marcado');
  btn.disabled = true;
  try {
    await api('/pedidos/chegada', {
      method: 'POST',
      body: JSON.stringify({ chave: el.dataset.chave, chegou: marcando }),
    });
    btn.classList.toggle('marcado', marcando);
    btn.textContent = marcando ? '📦 chegou' : 'marcar chegada';
    el.classList.toggle('chegou', marcando);
    el.dataset.estagio = marcando ? 'chegou' : 'ENVIADO';
    // Atualiza a etiqueta de estágio sem redesenhar a lista inteira.
    const etiqueta = el.querySelector('.peca-estagio');
    if (etiqueta) {
      etiqueta.className = `peca-estagio ${marcando ? 'e-chegou' : 'e-enviado'}`;
      etiqueta.textContent = marcando ? 'chegou' : 'a caminho';
    }
    toast(marcando ? 'Peça marcada como recebida' : 'Marcação desfeita', 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

let _estagioAtivo = '';

function filtrarPorEstagio(estagio) {
  _estagioAtivo = estagio;
  document.querySelectorAll('.pecas-filtro').forEach(b =>
    b.classList.toggle('ativo', b.dataset.estagio === estagio));
  filtrarPecas(document.getElementById('pecas-busca')?.value || '');
}

// Filtro local. Com 14 compras e crescendo, caçar uma peça rolando a lista
// inteira é trabalho manual que o computador faz melhor.
function filtrarPecas(termo) {
  const t = (termo || '').trim().toLowerCase();
  const linhas = document.querySelectorAll('.peca-linha');
  let visiveis = 0;
  linhas.forEach(el => {
    const bateTexto = !t || (el.dataset.busca || '').includes(t);
    // "pendente" não é estágio da compra e sim ausência de cliente — por isso
    // é tratado à parte em vez de virar mais um valor de data-estagio.
    const bateEstagio = !_estagioAtivo
      || (_estagioAtivo === 'pendente' ? el.dataset.pendente === '1'
                                       : el.dataset.estagio === _estagioAtivo);
    const bate = bateTexto && bateEstagio;
    el.style.display = bate ? '' : 'none';
    if (bate) visiveis++;
  });
  const contagem = document.getElementById('pecas-contagem');
  if (contagem) {
    contagem.textContent = t
      ? `${visiveis} de ${linhas.length}`
      : `${linhas.length} compra${linhas.length !== 1 ? 's' : ''}`;
  }
}

// A planilha devolve valor ora como "R$ 778,43", ora como "125,36" — depende
// de a célula ter formato de moeda ou não. Duas grafias na mesma coluna fazem
// a tela parecer quebrada. Normaliza para uma só na exibição.
function formatarValorPeca(bruto) {
  const texto = String(bruto ?? '').trim();
  if (!texto) return '—';
  const numero = parseFloat(texto.replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.'));
  if (!isFinite(numero)) return texto;
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// ─── Baixa no AgoraOS ───────────────────────────────────────────────
//
// O site lança a peça na OS do cliente no AgoraOS. Lançar item na OS É a baixa
// de estoque de lá: quem consome o saldo é a finalização da OS, não existe
// endpoint de "dar baixa" avulso.

function tratarRetornoAgoraOS(linha, cliente, peca, ag) {
  if (!ag || !ag.ativo) return;

  if (ag.estado === 'lancada' || ag.estado === 'ja_lancada') {
    toast(ag.mensagem, 'success');
    // O aviso de "sem controle de estoque" vai separado e sem sumir junto:
    // é o tipo de coisa que, ignorada, faz alguém confiar num saldo que não existe.
    if (ag.aviso) toast(ag.aviso, 'error');
    return;
  }

  if (ag.estado === 'erro') { toast(`AgoraOS: ${ag.mensagem}`, 'error'); return; }

  if (ag.estado === 'revisar') abrirModalAgoraOS(linha, cliente, peca, ag.previa, ag.mensagem);
}

function abrirModalAgoraOS(linha, cliente, peca, previa, motivo) {
  const corpo = document.getElementById('agoraos-corpo');
  document.getElementById('agoraos-motivo').textContent =
    `${cliente} · ${peca || 'sem peça'} — ${motivo || 'confirme onde lançar'}`;

  const os = previa.os ? [previa.os] : (previa.os_candidatas || []);
  const prods = previa.produto ? [previa.produto] : (previa.produto_candidatos || []);

  if (os.length === 0) {
    corpo.innerHTML = `<div class="vcep-erro" style="margin:0;">
      Esse cliente não tem OS em aberto no AgoraOS. Abra a OS por lá primeiro —
      o site não cria OS de propósito, pra não encher o sistema de ordem duplicada.
    </div>`;
    document.getElementById('btn-lancar-agoraos').style.display = 'none';
    document.getElementById('modal-agoraos').classList.add('open');
    return;
  }
  document.getElementById('btn-lancar-agoraos').style.display = '';

  corpo.innerHTML = `
    <div class="conc-titulo">Em qual OS?</div>
    ${os.map((o, i) => `
      <label class="conc-item" style="cursor:pointer;">
        <input type="radio" name="ag-os" value="${o.id}" ${i === 0 ? 'checked' : ''}>
        <div style="flex:1;min-width:0;">
          <div class="conc-cliente">OS ${o.id} · ${esc(o.status || '')}</div>
          <div class="conc-meta">${esc(o.data || '')}${o.aparelhos && o.aparelhos.length
            ? ' · ' + esc(o.aparelhos.join(', ')) : ''}</div>
        </div>
      </label>`).join('')}

    <div class="conc-titulo" style="margin-top:14px;">Qual peça do catálogo?</div>
    ${prods.length === 0
      ? `<div class="conc-alerta" style="margin:0;">Essa peça não existe no catálogo do
           AgoraOS. Cadastre por lá e vincule de novo.</div>`
      : prods.map((p, i) => `
      <label class="conc-item" style="cursor:pointer;">
        <input type="radio" name="ag-prod" value="${p.id_produto_extensao}" ${i === 0 ? 'checked' : ''}>
        <div style="flex:1;min-width:0;">
          <div class="conc-cliente">${esc(p.nome)}</div>
          <div class="conc-meta">R$ ${esc(p.preco || '0')}${p.controla_estoque
            ? '' : ' · sem controle de estoque no AgoraOS'}</div>
        </div>
      </label>`).join('')}

    <div class="conc-titulo" style="margin-top:14px;">Quantidade</div>
    <input type="number" id="ag-qtd" class="input" min="1" step="1" value="${previa.qtd || 1}"
           style="max-width:110px;">
  `;

  const btn = document.getElementById('btn-lancar-agoraos');
  btn.disabled = prods.length === 0;
  btn.onclick = () => lancarNoAgoraOS(linha, cliente, peca);
  document.getElementById('modal-agoraos').classList.add('open');
}

async function lancarNoAgoraOS(linha, cliente, peca) {
  const idOs = document.querySelector('input[name="ag-os"]:checked')?.value;
  const idProd = document.querySelector('input[name="ag-prod"]:checked')?.value;
  const qtd = parseFloat(document.getElementById('ag-qtd')?.value || '1');

  if (!idOs || !idProd) { toast('Escolha a OS e a peça', 'error'); return; }

  const btn = document.getElementById('btn-lancar-agoraos');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Lançando...';

  try {
    const r = await api(`/pedidos/${linha}/agoraos`, {
      method: 'POST',
      body: JSON.stringify({ id_os: idOs, id_produto_extensao: idProd,
                             qtd, cliente, peca }),
    });
    fecharModais();
    toast(r.mensagem, 'success');
    if (r.aviso) toast(r.aviso, 'error');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Lançar na OS';
  }
}

async function criarTecnico() {
  const input = document.getElementById('novo-tecnico-nome');
  const nome = input.value.trim();
  if (!nome) { toast('Informe o nome do técnico', 'error'); return; }

  try {
    await api('/tecnicos', { method: 'POST', body: JSON.stringify({ nome }) });
    fecharModais();
    toast(`Técnico "${nome}" criado!`, 'success');
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
}

async function deletarTecnico(evt, id) {
  evt.stopPropagation();
  // A confirmação não promete mais "remove tudo": se já tem ficha ligada, o
  // servidor desativa em vez de apagar (preserva histórico faturado).
  if (!confirm('Remover este técnico? Se ele já tiver ficha registrada, ' +
               'fica desativado em vez de apagado, pra não perder o histórico.')) return;

  try {
    const r = await api(`/tecnicos/${id}`, { method: 'DELETE' });
    if (fichaAtiva?.tecnico_id === id) mostrarEstadoVazio();
    await carregarTecnicos();
    toast(r.mensagem || (r.desativado ? 'Técnico desativado' : 'Técnico removido'), 'info');
  } catch (e) { toast(e.message, 'error'); }
}

function mostrarDetalhe() {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('ficha-detail').style.display = 'block';
}

function mostrarEstadoVazio() {
  fichaAtiva = null;
  document.getElementById('empty-state').style.display = 'flex';
  document.getElementById('ficha-detail').style.display = 'none';
}

async function selecionarFicha(id) {
  mostrarDetalhe();
  await renderFichaDetalhe(id);
}

async function renderFichaDetalhe(id) {
  // Aceita o ID ou a FICHA INTEIRA.
  //
  // `fichaAtiva` guarda o objeto da ficha, e quatro pontos do código chamam
  // `renderFichaDetalhe(fichaAtiva)` — inclusive o auto-refresh. Com o objeto,
  // a URL virava `/api/fichas/[object Object]`, que não casa com rota nenhuma
  // e devolvia o 404 GENÉRICO do servidor: "The requested URL was not found".
  // Como o auto-refresh roda a cada 10s, o erro reaparecia sem parar e a tela
  // vivia recarregando — foi o "site travando" relatado pelo Kalebe em
  // 2026-08-18.
  //
  // Normalizar aqui conserta os quatro pontos de uma vez e deixa a função à
  // prova do próximo lugar que chamar do jeito errado.
  const fichaId = (id && typeof id === 'object') ? id.id : id;

  const detail = document.getElementById('ficha-detail');

  if (fichaId === undefined || fichaId === null || fichaId === '') {
    detail.innerHTML = `<div class="vcep-erro" style="margin:0;">Ficha não identificada. Escolha uma rota na barra lateral.</div>`;
    return;
  }

  detail.innerHTML = `<div class="loading-row" style="height:200px;display:flex;align-items:center;justify-content:center;gap:10px;"><div class="spinner"></div><span style="color:var(--text-muted);">Carregando roteiro...</span></div>`;

  if (mapaLeaflet) { mapaLeaflet.remove(); mapaLeaflet = null; }

  let ficha, servicos, resumo;
  try {
    ({ ficha, servicos, resumo } = await api(`/fichas/${fichaId}`));
  } catch (e) {
    detail.innerHTML = `<div class="vcep-erro" style="margin:0;">Não foi possível carregar esta ficha: ${esc(e.message)}</div>`;
    toast(e.message, 'error');
    return;
  }

  fichaAtiva = ficha;
  servicosAtuais = servicos;
  const tecnico = tecnicos.find(t => t.id === ficha.tecnico_id);
  const cor = escCor(tecnico?.cor);

  const temPartida = ficha.ponto_partida_lat != null && ficha.ponto_partida_lat !== 0;
  const distKm = resumo?.distancia_km ?? ficha.distancia_total ?? 0;
  const tempo  = resumo?.tempo_minutos ?? 0;
  const temCoordenadas = temPartida ||
    servicos.some(s => s.lat && s.lng && (s.lat !== 0 || s.lng !== 0));
  const semCoord = resumo?.sem_coordenada || 0;

  detail.innerHTML = `
    <div class="ficha-header">
      <div>
        <div style="font-size:11px;font-weight:600;color:${cor};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;display:flex;align-items:center;gap:5px;">${icone('usuario', 'icone-11')} ${esc(tecnico?.nome) || '—'}</div>
        <div class="ficha-titulo">
          ${esc(ficha.dia_semana)}
          ${ficha.status === 'concluida' ? `<span class="tag-concluida">${icone('concluir', 'icone-11')} Concluída</span>` : ''}
        </div>
        <div class="ficha-sub">${ficha.data_referencia ? `<span style="display:inline-flex;align-items:center;gap:4px;">${icone('calendario', 'icone-12')} ${esc(formatarData(ficha.data_referencia))}</span> · ` : ''}Criado em ${esc(formatarDataHora(ficha.created_at))}</div>
      </div>
      <div class="ficha-acoes">
        <button class="btn btn-primary" onclick="abrirModalAddServico(${ficha.id})">+ Adicionar Atendimento</button>
        <button class="btn btn-ghost" onclick="transferirFicha(${ficha.id})"
                title="Passar a rota inteira para outro técnico"
                style="display:flex;align-items:center;gap:6px;">${icone('usuario', 'icone-13')} Transferir rota</button>
        <button class="btn btn-ghost" id="btn-abrir-maps" style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          Abrir no Google Maps
        </button>
        <button class="btn btn-ghost" id="btn-whatsapp-rota" style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          Enviar por WhatsApp
        </button>
        <button class="btn ${ficha.status === 'concluida' ? 'btn-ghost' : 'btn-primary'}" id="btn-concluir-rota" style="display:flex;align-items:center;gap:6px;" onclick="alternarStatusFicha(${ficha.id}, '${ficha.status || 'pendente'}')">
          ${icone('concluir', 'icone-14')}
          ${ficha.status === 'concluida' ? 'Reabrir Rota' : 'Concluir Rota'}
        </button>
      </div>
    </div>

    ${semCoord > 0 ? `<div class="vcep-aviso" style="margin-bottom:18px;">${semCoord} atendimento${semCoord > 1 ? 's' : ''} sem coordenada — não entra${semCoord > 1 ? 'm' : ''} no cálculo da rota. Remova e cadastre de novo para corrigir.</div>` : ''}

    <div class="stats-strip">
      <div class="stat-card"><div class="stat-label">Atendimentos Técnicos</div><div class="stat-value" style="color:${cor}"><span class="stat-num" id="stat-num-pontos">0</span><span class="stat-unit">pts</span></div></div>
      <div class="stat-card"><div class="stat-label">Distância Estimada</div><div class="stat-value" style="color:${cor}"><span class="stat-num" id="stat-num-dist">${distKm > 0 ? '0,0' : '—'}</span><span class="stat-unit">km</span></div></div>
      <div class="stat-card"><div class="stat-label">Tempo Total (c/ serviços)</div><div class="stat-value" style="color:${cor}"><span class="stat-num" id="stat-num-tempo">${tempo > 0 ? '0min' : '—'}</span><span class="stat-unit"></span></div></div>
    </div>

    <div class="content-map-grid">
      <div class="content-col">
        <div class="panel-grid">
          <div class="panel">
            <div class="panel-header"><div class="panel-icon">${icone('casa', 'icone-15')}</div><span class="panel-title">Ponto de Partida</span></div>
            <div class="panel-body">
              ${temPartida
                ? `<div style="font-family:var(--font-mono);font-size:13px;color:${cor};margin-bottom:4px;">${esc(formatCEP(ficha.ponto_partida_cep))}</div>
                   <div style="font-size:12px;color:var(--text-secondary);">${esc(ficha.ponto_partida) || 'Endereço não informado'}</div>
                   <div style="margin-top:12px;"><a href="https://www.openstreetmap.org/?mlat=${ficha.ponto_partida_lat}&mlon=${ficha.ponto_partida_lng}&zoom=15" target="_blank" rel="noopener" style="font-size:11px;color:${cor};text-decoration:none;">↗ Ver no mapa</a></div>`
                : `<div style="color:var(--text-muted);font-size:12px;">Nenhum ponto de partida configurado.<br>Sem ele a rota não pode ser otimizada.</div>`}
            </div>
          </div>
          <div class="panel">
            <div class="panel-header"><div class="panel-icon">${icone('raio', 'icone-15')}</div><span class="panel-title">Otimização de Rota</span></div>
            <div class="panel-body">
              ${temPartida
                ? `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:14px;">Nearest Neighbor + refinamento <strong>2-opt</strong>, recalculado ao adicionar ou remover atendimentos.<br><br><span style="color:var(--text-muted);font-size:11px;display:inline-flex;align-items:center;gap:4px;">${icone('info', 'icone-11')} Distância por ruas (linha reta × 1.4) · 40 km/h médios · 20 min por parada</span></div>
                   <button class="btn btn-ghost btn-full" onclick="forcarOtimizacao(${ficha.id})">${icone('atualizar', 'icone-13')} Recalcular Rota Agora</button>`
                : `<div style="font-size:12px;color:var(--text-muted);">Adicione um CEP de partida para ativar a otimização.</div>`}
            </div>
          </div>
        </div>
        <div class="roteiro-container">
          <div class="roteiro-header">
            <span class="roteiro-title">${icone('mapa', 'icone-14')} Roteiro Ordenado</span>
            ${servicos.length > 0 ? `<span class="badge accent">${servicos.length} parada${servicos.length !== 1 ? 's' : ''}</span>` : ''}
          </div>
          ${renderRoteiro(ficha, servicos, cor)}
        </div>
      </div>
      <div class="mapa-col">
        <div class="mapa-wrapper">
          <div class="mapa-header">
            <div class="panel-icon">${icone('mapa', 'icone-15')}</div>
            <span class="panel-title">Mapa do Roteiro</span>
            ${temCoordenadas ? `<span class="badge accent" style="margin-left:auto;">${servicos.length} atendimento${servicos.length !== 1 ? 's' : ''}</span>` : ''}
          </div>
          <div id="mapa-roteiro" class="mapa-container">
            ${!temCoordenadas ? `<div class="mapa-empty"><div style="margin-bottom:8px;">${icone('pin', 'icone-28')}</div><div style="font-size:12px;color:var(--text-muted);">Adicione atendimentos com<br>coordenadas para ver o mapa</div></div>` : ''}
          </div>
          ${renderClientesRota(servicos)}
        </div>
      </div>
    </div>`;

  const btnMaps = document.getElementById('btn-abrir-maps');
  if (btnMaps) btnMaps.addEventListener('click', () => abrirRotaGoogleMaps(ficha, servicos));

  const btnWhats = document.getElementById('btn-whatsapp-rota');
  if (btnWhats) btnWhats.addEventListener('click', () => enviarRotaWhatsApp(ficha, servicos));

  if (temCoordenadas) {
    inicializarMapa('mapa-roteiro');
    renderizarMapaPontos(ficha, servicos, cor);
  }

  if (servicos.length > 1) inicializarDragRoteiro(ficha.id);

  // Fotos vêm depois e sem await: a rota já está na tela, e esperar as
  // imagens para mostrar o roteiro seria trocar velocidade por nada.
  carregarFotosDoRoteiro(servicos.map(s => s.id));

  animarNumero(document.getElementById('stat-num-pontos'), servicos.length);
  if (distKm > 0) {
    animarNumero(document.getElementById('stat-num-dist'), distKm, {
      formatar: v => v.toFixed(1).replace('.', ','),
    });
  }
  if (tempo > 0) {
    animarNumero(document.getElementById('stat-num-tempo'), tempo, {
      formatar: v => formatarTempo(Math.round(v)),
    });
  }
}

// Conta de 0 até valorFinal com easing, formatando cada quadro.
// Usado nos cartões de estatística — reforça que o roteiro acabou de ser calculado.
function animarNumero(el, valorFinal, opcoes = {}) {
  if (!el || !isFinite(valorFinal)) return;
  const { formatar = v => String(Math.round(v)), duracaoMs = 700 } = opcoes;
  const inicio = performance.now();

  el.classList.add('numero-vivo');

  function passo(agora) {
    const t = Math.min((agora - inicio) / duracaoMs, 1);
    const facilitado = 1 - Math.pow(1 - t, 3);
    el.textContent = formatar(valorFinal * facilitado);
    if (t < 1) {
      requestAnimationFrame(passo);
    } else {
      el.textContent = formatar(valorFinal);
      setTimeout(() => el.classList.remove('numero-vivo'), 260);
    }
  }
  requestAnimationFrame(passo);
}

function renderRoteiro(ficha, servicos, cor = 'var(--accent)') {
  if (servicos.length === 0) {
    return `<div class="loading-row" style="padding:40px;text-align:center;"><div style="margin-bottom:8px;">${icone('pin', 'icone-24')}</div><div>Nenhum atendimento adicionado ainda.</div><div style="font-size:11px;margin-top:4px;color:var(--text-muted);">Clique em "+ Adicionar Atendimento" para montar o roteiro.</div></div>`;
  }

  const partida = ficha.ponto_partida
    ? `<div class="partida-strip"><div class="step-num partida">${icone('estrela', 'icone-16')}</div><div><div class="partida-label">Ponto de Partida</div><div class="partida-text">${esc(ficha.ponto_partida)}</div></div></div>`
    : '';

  const ordenados = [...servicos].sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999));

  const items = ordenados.map((s, i) => {
    const aparelho = [s.tipo_aparelho, s.modelo].filter(Boolean).join(' — ');
    const feito = s.status === 'concluido';
    return `
      <div class="roteiro-item ${feito ? 'roteiro-item-concluido' : ''}" id="svc-${s.id}" data-id="${s.id}">
        <div class="drag-handle" title="Arraste para reordenar">⠿</div>
        <!-- O NÚMERO conclui o atendimento. Pendente, abre a folha do desfecho
             ("o que aconteceu?"); concluído, reabre direto. É o alvo dentro da
             ordem de atendimento, que é onde quem acompanha a rota está
             olhando. -->
        <button class="step-num step-num-btn" style="background:${cor}20;border-color:${cor}60;color:${cor}"
                onclick="${feito
                  ? `alternarStatusServico(${s.id},'pendente',${ficha.id})`
                  : `abrirDesfecho(${s.id},${ficha.id})`}"
                title="${feito ? 'Reabrir atendimento' : 'Concluir e registrar o que aconteceu'}">
          ${feito ? icone('check', 'icone-13') : i + 1}
        </button>
        <div class="roteiro-info">
          <div class="roteiro-cep" style="color:${cor}">${esc(formatCEP(s.cep))}</div>
          <div class="roteiro-endereco">${s.numero ? `<strong>Nº ${esc(s.numero)}</strong> · ` : ''}${esc(s.endereco_completo) || '—'}</div>
          ${s.cliente ? `<div class="roteiro-cliente">${icone('usuario', 'icone-11')} ${esc(s.cliente)}${s.descricao ? ' · ' + esc(s.descricao) : ''}</div>` : ''}
          ${s.telefone ? `<div class="roteiro-cliente">${icone('telefone', 'icone-11')} <a href="tel:${esc(s.telefone.replace(/\D/g, ''))}" onclick="event.stopPropagation()">${esc(s.telefone)}</a></div>` : ''}
          ${aparelho ? `<div class="roteiro-aparelho">${icone('ferramenta', 'icone-11')} ${esc(aparelho)}</div>` : ''}
          ${(() => {
            const st = setorPorId(s.setor_id);
            const os = s.numero_os ? `<span class="roteiro-os">OS ${esc(s.numero_os)}</span>` : '';
            const marca = st
              ? `<span class="roteiro-setor" style="color:${escCor(st.cor)};border-color:${escCor(st.cor)}55;background:${escCor(st.cor)}18;">${esc(st.nome)}</span>`
              : '';
            return (os || marca) ? `<div class="roteiro-etiquetas">${marca}${os}</div>` : '';
          })()}
          ${seloDesfecho(s)}
          <div class="roteiro-fotos" id="fotos-${s.id}"></div>
          ${(!s.lat || !s.lng) ? `<div class="roteiro-cliente" style="color:var(--danger-text);display:flex;align-items:center;gap:4px;">${icone('alerta', 'icone-11')} sem coordenada — fora do cálculo</div>` : ''}
        </div>
        <div class="roteiro-actions">
          ${(s.lat && s.lng) ? `<a href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lng}&zoom=16" target="_blank" rel="noopener" title="Ver no mapa" style="color:${cor};padding:4px 8px;display:inline-flex;">${icone('externo', 'icone-13')}</a>` : ''}
          ${(s.lat && s.lng) ? `<a href="https://waze.com/ul?ll=${s.lat},${s.lng}&navigate=yes" target="_blank" rel="noopener" title="Navegar com Waze" style="color:${cor};padding:4px 8px;display:inline-flex;">${icone('navegacao', 'icone-13')}</a>` : ''}
          <button class="btn-a-caminho" onclick="avisarACaminho(${s.id})" title="Avisar no WhatsApp que está a caminho deste cliente">A caminho</button>
          <button class="btn-editar" onclick="abrirModalEditarServico(${s.id})" title="Editar, reagendar ou mudar de técnico">${icone('editar', 'icone-12')}</button>
          <button class="btn-remove" onclick="removerServico(${s.id},${ficha.id})">${icone('x', 'icone-11')}</button>
        </div>
      </div>`;
  }).join('');

  return partida + `<div class="roteiro-lista" id="roteiro-lista">${items}</div>`;
}

// ─── "A caminho": avisa o grupo do WhatsApp sobre um cliente ────────────
// Fica na linha do cliente, dentro do roteiro, porque a mensagem é sobre
// AQUELE atendimento — o nome do cliente e o endereço saem do próprio ponto.
//
// Não dispara sozinho, e isso é decisão tomada depois de três tentativas
// falharem no celular: window.open é barrado por bloqueador de pop-up,
// location.href é atropelado pela navegação seguinte, e navigator.share varia
// por aparelho. Todas falham em SILÊNCIO. Um link que o usuário toca não
// depende de permissão nenhuma e funciona em qualquer lugar.
function montarMensagemACaminho(s, tecnicoNome, linkAcompanhar) {
  const partes = [];
  partes.push(`🚗 Técnico ${tecnicoNome || ''} a caminho do cliente ${s.cliente || 'sem nome'}`.trim());
  if (s.endereco_completo) partes.push(`📍 ${s.endereco_completo}`);
  if (linkAcompanhar) partes.push(`Acompanhe a chegada:
${linkAcompanhar}`);
  if (s.lat && s.lng) {
    partes.push(`https://waze.com/ul?ll=${s.lat},${s.lng}&navigate=yes`);
  } else if (s.endereco_completo || s.cep) {
    partes.push(`https://waze.com/ul?q=${encodeURIComponent(s.endereco_completo || s.cep)}&navigate=yes`);
  }
  return partes.join('\n\n');
}

async function avisarACaminho(servicoId) {
  const s = servicosAtuais.find(x => x.id === servicoId);
  if (!s) { toast('Atendimento não encontrado', 'error'); return; }

  const tecnico = tecnicos.find(t => t.id === fichaAtiva?.tecnico_id);

  // O link de acompanhamento nasce aqui, no servidor, e entra na mensagem.
  // Se falhar, segue sem ele — avisar sem acompanhamento é melhor que nada.
  let link = null;
  try {
    const r = await api(`/servicos/${servicoId}/rastreio`, { method: 'POST' });
    link = `${location.origin}/acompanhar/${r.token}`;
  } catch (e) { console.warn('Sem link de acompanhamento:', e.message); }

  const texto = montarMensagemACaminho(s, tecnico?.nome, link);

  document.getElementById('acaminho-msg').textContent = texto;

  // whatsapp:// abre o aplicativo direto na tela de escolher conversa, com o
  // grupo entre as recentes. No desktop esse esquema não existe: vai wa.me.
  const ehCelular = /android|iphone|ipad|ipod/i.test(navigator.userAgent);
  document.getElementById('acaminho-whats').href = ehCelular
    ? `whatsapp://send?text=${encodeURIComponent(texto)}`
    : `https://wa.me/?text=${encodeURIComponent(texto)}`;

  // Copiar é a última garantia: se o link não abrir naquele aparelho, ainda
  // dá para colar no WhatsApp à mão. Nunca fica sem saída.
  document.getElementById('acaminho-copiar').onclick = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      toast('Mensagem copiada', 'success');
    } catch {
      const campo = document.createElement('textarea');
      campo.value = texto;
      document.body.appendChild(campo);
      campo.select();
      try { document.execCommand('copy'); toast('Mensagem copiada', 'success'); }
      catch { toast('Não consegui copiar — selecione o texto acima', 'error'); }
      campo.remove();
    }
  };

  document.getElementById('modal-a-caminho').classList.add('open');
}

let servicosAtuais  = [];   // últimos serviços carregados (com lat/lng), pra redesenhar o mapa sem refetch
let sortableRoteiro = null;

// Liga o arraste na lista de paradas. Chamado toda vez que a ficha é
// (re)renderizada — precisa destruir a instância anterior, senão fica
// presa a um elemento do DOM que já não existe mais.
function inicializarDragRoteiro(fichaId) {
  const lista = document.getElementById('roteiro-lista');
  if (!lista || typeof Sortable === 'undefined') return;

  if (sortableRoteiro) { sortableRoteiro.destroy(); sortableRoteiro = null; }

  sortableRoteiro = new Sortable(lista, {
    handle: '.drag-handle',
    animation: 180,
    ghostClass: 'roteiro-item-ghost',
    dragClass: 'roteiro-item-dragging',
    onEnd: () => aoSoltarReordenacao(fichaId),
  });
}

// Depois de soltar: renumera na hora (sem esperar rede), manda a nova
// ordem pro servidor em segundo plano, e só atualiza números + mapa —
// nunca recarrega a ficha inteira, pra não piscar tudo de novo.
async function aoSoltarReordenacao(fichaId) {
  const lista = document.getElementById('roteiro-lista');
  if (!lista) return;

  const itens = Array.from(lista.children);
  const novaOrdemIds = itens.map(el => parseInt(el.dataset.id, 10));

  itens.forEach((el, i) => {
    const numEl = el.querySelector('.step-num');
    if (numEl) numEl.textContent = i + 1;
  });

  try {
    const r = await api(`/fichas/${fichaId}/reordenar`, {
      method: 'PUT',
      body: JSON.stringify({ ordem_ids: novaOrdemIds }),
    });

    if (r.distancia_total > 0) {
      animarNumero(document.getElementById('stat-num-dist'), r.distancia_total, {
        formatar: v => v.toFixed(1).replace('.', ','),
      });
    }
    if (r.tempo_minutos > 0) {
      animarNumero(document.getElementById('stat-num-tempo'), r.tempo_minutos, {
        formatar: v => formatarTempo(Math.round(v)),
      });
    }

    const porId = new Map(servicosAtuais.map(s => [s.id, s]));
    const reordenados = novaOrdemIds.map(id => porId.get(id)).filter(Boolean);
    if (reordenados.length === servicosAtuais.length) servicosAtuais = reordenados;

    if (fichaAtiva) {
      const tecnico = tecnicos.find(t => t.id === fichaAtiva.tecnico_id);
      renderizarMapaPontos(fichaAtiva, servicosAtuais, escCor(tecnico?.cor));
    }
  } catch (e) {
    toast(`Não foi possível salvar a nova ordem: ${e.message}`, 'error');
    await renderFichaDetalhe(fichaId); // estado local pode ter ficado incoerente — recarrega do zero
  }
}

let clientesRotaAtual = [];

function renderClientesRota(servicos) {
  const ordenados = [...servicos].sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999));
  clientesRotaAtual = ordenados.map(s => (s.cliente || '').trim());

  if (ordenados.length === 0) return '';

  const itensHtml = ordenados.map((s, i) => `
    <div class="cliente-linha">
      <span class="cliente-num">${i + 1}</span>
      <span class="cliente-nome">${s.cliente ? esc(s.cliente) : '<em>Sem nome</em>'}</span>
    </div>`).join('');

  return `
    <div class="clientes-rota">
      <div class="clientes-rota-header">
        <span class="panel-title">${icone('usuario', 'icone-14')} Clientes da Rota</span>
        <button class="btn btn-ghost btn-copiar" onclick="copiarClientesRota()" id="btn-copiar-clientes">
          ${icone('clipboard', 'icone-12')} Copiar lista
        </button>
      </div>
      <div class="clientes-rota-lista">${itensHtml}</div>
    </div>`;
}

function copiarClientesRota() {
  if (clientesRotaAtual.length === 0) { toast('Nenhum cliente na rota', 'error'); return; }

  const texto = clientesRotaAtual
    .map((nome, i) => `${i + 1}. ${nome || 'Sem nome'}`)
    .join('\n');

  const _sucesso = () => {
    toast('Lista de clientes copiada!', 'success');
    const btn = document.getElementById('btn-copiar-clientes');
    if (btn) {
      const original = btn.innerHTML;
      btn.innerHTML = `${icone('check', 'icone-12')} Copiado!`;
      setTimeout(() => { btn.innerHTML = original; }, 1800);
    }
  };

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto).then(_sucesso).catch(() => _copiarFallback(texto, _sucesso));
  } else {
    _copiarFallback(texto, _sucesso);
  }
}

// Fallback pra navegadores/WebViews antigos sem Clipboard API (comuns em
// celular Android mais velho que técnico de campo costuma usar).
function _copiarFallback(texto, aoSucesso) {
  const area = document.createElement('textarea');
  area.value = texto;
  area.style.position = 'fixed';
  area.style.left = '-9999px';
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand('copy');
    aoSucesso();
  } catch {
    toast('Não foi possível copiar automaticamente. Selecione o texto manualmente.', 'error');
  } finally {
    document.body.removeChild(area);
  }
}

// Formata o roteiro do dia como texto e abre o WhatsApp pra escolher pra
// quem mandar (wa.me sem número abre o seletor de contato/conversa —
// não é uma mensagem fixa pro número da empresa, é o técnico compartilhando
// a própria rota com quem ele quiser: despacho, outro técnico, etc.).
function enviarRotaWhatsApp(ficha, servicos) {
  const ordenados = [...servicos].sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999));

  if (ordenados.length === 0) {
    toast('Nenhum atendimento na rota ainda', 'error');
    return;
  }

  const linhas = [];
  linhas.push(`*Roteiro — ${ficha.dia_semana}*`);
  if (ficha.data_referencia) linhas.push(formatarData(ficha.data_referencia));
  if (ficha.ponto_partida) linhas.push(`📍 Partida: ${ficha.ponto_partida}`);
  linhas.push('');

  ordenados.forEach((s, i) => {
    const endereco = s.numero ? `Nº ${s.numero} · ${s.endereco_completo || ''}` : (s.endereco_completo || '—');
    const aparelho = [s.tipo_aparelho, s.modelo].filter(Boolean).join(' — ');
    linhas.push(`${i + 1}. ${endereco}`);
    if (s.cliente) linhas.push(`   Cliente: ${s.cliente}`);
    if (aparelho) linhas.push(`   Aparelho: ${aparelho}`);
    if (s.descricao) linhas.push(`   Obs: ${s.descricao}`);
  });

  if (ficha.distancia_total > 0) {
    linhas.push('');
    linhas.push(`Distância estimada: ${fmtKm(ficha.distancia_total)} km`);
  }

  const texto = linhas.join('\n');
  window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`, '_blank', 'noopener,noreferrer');
}

function abrirRotaGoogleMaps(ficha, servicos) {
  const ordenados = [...servicos]
    .sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999))
    .filter(s => s.endereco_completo);

  if (ordenados.length === 0) { toast('Nenhum atendimento com endereço válido', 'error'); return; }

  if (ordenados.length > 11) {
    toast(`Rota com ${ordenados.length} paradas — o Google Maps só aceita 11 por link. Abrindo as 11 primeiras.`, 'info');
  }
  const usar = ordenados.slice(0, 11);

  function endTexto(s) {
    let end = s.endereco_completo || '';
    if (s.numero) {
      const idx = end.indexOf(',');
      end = idx !== -1 ? end.slice(0, idx) + ', ' + s.numero + end.slice(idx)
                       : end + ', ' + s.numero;
    }
    if (s.cep) end += `, ${formatCEP(s.cep)}`;
    return end;
  }

  const temPartida = ficha.ponto_partida && ficha.ponto_partida.trim();
  let origin, destination, waypointList;

  if (temPartida) {
    origin = ficha.ponto_partida_cep
      ? `${ficha.ponto_partida}, ${formatCEP(ficha.ponto_partida_cep)}`
      : ficha.ponto_partida;
    destination = endTexto(usar[usar.length - 1]);
    waypointList = usar.slice(0, -1).map(endTexto);
  } else {
    origin = endTexto(usar[0]);
    destination = endTexto(usar[usar.length - 1]);
    waypointList = usar.slice(1, -1).map(endTexto);
  }

  const params = new URLSearchParams({ api: '1', origin, destination, travelmode: 'driving' });
  let url = `https://www.google.com/maps/dir/?${params.toString()}`;
  if (waypointList.length > 0) {
    url += `&waypoints=${waypointList.map(encodeURIComponent).join('|')}`;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

let verificacaoAtual = null;
let vcepTabAtual     = 'analise';
let vcepExpandido    = null;

const ZONA_LABEL = {
  centro: 'Centro', norte: 'Zona Norte', sul: 'Zona Sul',
  leste: 'Zona Leste', oeste: 'Zona Oeste', outros: 'Região',
};
const DIAS_SEMANA_FULL = ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado'];
const DIAS_ABREV = {
  'Segunda-feira':'SEG','Terça-feira':'TER','Quarta-feira':'QUA',
  'Quinta-feira':'QUI','Sexta-feira':'SEX','Sábado':'SAB',
};

function _ini(nome) {
  const partes = String(nome || '?').trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return '?';
  return partes.map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

function _hexRgb(h) {
  const c = escCor(h);
  return `${parseInt(c.slice(1,3),16)},${parseInt(c.slice(3,5),16)},${parseInt(c.slice(5,7),16)}`;
}

// Única fonte de verdade pra "essa rota serve ou não" — usada no número,
// na barra e no selo do card. Antes disso existiam duas escalas soltas
// (cor por faixa + palavra por faixa) que podiam se contradizer.
// A classificação vem PRONTA do servidor (campo `classificacao`). Esta função
// só traduz para texto e cor. Antes ela tinha régua própria (100/50) que
// divergia do SCORE_MINIMO_BOM = 30 do backend, e o mesmo card saía com selo
// "Melhor encaixe" e nota de "Não recomendado" ao mesmo tempo.
const ENCAIXE_ESTILO = {
  bem:      { texto: 'Encaixa bem',   classe: 'bom',   cor: 'var(--success)' },
  razoavel: { texto: 'Dá pra encaixar', classe: 'medio', cor: 'var(--gold)' },
  fora:     { texto: 'Fora de mão',   classe: 'ruim',  cor: 'var(--danger)' },
};

// Escala FIXA da barra. Antes era `score / maior score da lista`, então a
// primeira opção sempre aparecia com a barra cheia — mesmo quando todas eram
// ruins. Um CEP na porta do técnico e um em Guarulhos davam a mesma barra.
// Agora 100 (o corte de "encaixa bem") é a referência: opção ruim parece ruim.
const ESCALA_BARRA = 150;

function _encaixeInfo(s) {
  if (s.vazia) {
    return { texto: 'Rota vazia', classe: 'vazio', cor: 'var(--text-muted)' };
  }
  return ENCAIXE_ESTILO[s.classificacao] || ENCAIXE_ESTILO.fora;
}

function _motivos(s, rank) {
  const m = [];
  const d = s.dist_minima;

  if (s.vazia) {
    m.push({ tipo:'pos', titulo:'Rota ainda vazia',
             desc:'Nenhum atendimento marcado — este CEP definiria o trajeto do dia' });
    if (d === null || d === undefined) {
      m.push({ tipo:'neg', titulo:'Sem ponto de partida',
               desc:'Cadastre o CEP de partida para a rota ser otimizada' });
    } else if (d <= 10) {
      m.push({ tipo:'pos', titulo:'Perto da base', desc:`${fmtKm(d)} km do ponto de partida` });
    } else {
      m.push({ tipo:'neu', titulo:'Distante da base', desc:`${fmtKm(d)} km do ponto de partida` });
    }
    return m;
  }

  if (s.mesma_zona) {
    m.push({ tipo:'pos', titulo:'Mesma zona geográfica',
             desc:`${s.pontos_mesma_zona} de ${s.total_pontos} pts já na ${ZONA_LABEL[s.zona_alvo] || 'mesma zona'}` });
  }

  if (d <= 10)      m.push({ tipo:'pos', titulo:'Atendimento muito próximo', desc:`${fmtKm(d)} km do atendimento mais próximo nessa rota` });
  else if (d <= 20) m.push({ tipo:'neu', titulo:'Distância moderada',   desc:`${fmtKm(d)} km — aceitável, mas aumenta o trajeto` });
  else              m.push({ tipo:'neg', titulo:'Distância alta',       desc:`${fmtKm(d)} km — pode desviar bastante a rota` });

  if (s.total_pontos >= 10) {
    m.push({ tipo:'neu', titulo:'Rota densa', desc:`${s.total_pontos} pontos nesse dia — confira a capacidade do técnico` });
  } else {
    m.push({ tipo:'pos', titulo:'Rota com espaço', desc:`Apenas ${s.total_pontos} pontos — boa capacidade disponível` });
  }

  if (rank === 0) {
    m.push({ tipo:'pos', titulo:'Melhor opção disponível',
             desc:'Maior pontuação entre as rotas analisadas para esse CEP' });
  } else if (d > 15) {
    m.push({ tipo:'neg', titulo:'Encaixe fraco',
             desc:'Distância alta — não é a rota prioritária para essa região' });
  }

  return m.slice(0, 4);
}

async function verificarCEP() {
  const cepInput = document.getElementById('verificar-cep-input');
  const cep = (cepInput.value || '').replace(/\D/g, '');

  if (cep.length !== 8) { toast('Informe um CEP válido', 'error'); return; }

  const btn = document.getElementById('btn-verificar');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';

  const resultado = document.getElementById('verificar-resultado');
  resultado.innerHTML = '';
  vcepTabAtual = 'analise';
  vcepExpandido = null;
  _vcepEsconderComparacao();

  try {
    const r = await api('/verificar-cep', { method: 'POST', body: JSON.stringify({ cep }) });
    verificacaoAtual = r;
    _renderVcep(resultado, r);
    _vcepSalvarHistorico(cep, r.endereco);
    if (r.preciso === false) {
      toast('Endereço aproximado (centroide do CEP)', 'info');
    }
  } catch (e) {
    resultado.innerHTML = `<div class="vcep-erro">${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Verificar';
  }
}

async function verificarEndereco() {
  const input = document.getElementById('verificar-endereco-input');
  const endereco = (input.value || '').trim();

  if (endereco.length < 6) { toast('Descreva o endereço com mais detalhes', 'error'); return; }

  const btn = document.getElementById('btn-verificar-endereco');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';

  const resultado = document.getElementById('verificar-resultado');
  resultado.innerHTML = '';
  vcepTabAtual = 'analise';
  vcepExpandido = null;
  _vcepEsconderComparacao();

  try {
    const r = await api('/verificar-endereco', { method: 'POST', body: JSON.stringify({ endereco }) });
    verificacaoAtual = r;
    _renderVcep(resultado, r);
    if (r.cep) _vcepSalvarHistorico(r.cep, r.endereco);
    if (r.preciso === false) {
      toast('Localização aproximada — confira o endereço encontrado', 'info');
    }
  } catch (e) {
    resultado.innerHTML = `<div class="vcep-erro">${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Verificar';
  }
}

function alternarModoBusca() {
  const linhaCep = document.getElementById('linha-busca-cep');
  const linhaEnd = document.getElementById('linha-busca-endereco');
  const botao = document.getElementById('btn-modo-busca');
  const modoEndereco = linhaEnd.style.display !== 'none';

  linhaCep.style.display = modoEndereco ? 'flex' : 'none';
  linhaEnd.style.display = modoEndereco ? 'none' : 'flex';
  botao.textContent = modoEndereco ? 'Buscar por endereço' : 'Buscar por CEP';

  if (!modoEndereco) {
    setTimeout(() => document.getElementById('verificar-endereco-input')?.focus(), 60);
  }
}

// ===== HISTÓRICO DE CEPs VERIFICADOS (localStorage — só neste navegador) =====
const VCEP_HISTORICO_CHAVE = 'portotec_vcep_historico';
const VCEP_HISTORICO_MAX = 8;

function _vcepCarregarHistorico() {
  try {
    return JSON.parse(localStorage.getItem(VCEP_HISTORICO_CHAVE) || '[]');
  } catch {
    return [];
  }
}

function _vcepSalvarHistorico(cep, endereco) {
  if (!cep) return;
  let lista = _vcepCarregarHistorico().filter(h => h.cep !== cep);
  lista.unshift({ cep, endereco: endereco || '', quando: Date.now() });
  lista = lista.slice(0, VCEP_HISTORICO_MAX);
  localStorage.setItem(VCEP_HISTORICO_CHAVE, JSON.stringify(lista));
  _vcepRenderHistorico();
}

function _vcepRenderHistorico() {
  const container = document.getElementById('vcep-historico');
  if (!container) return;

  const lista = _vcepCarregarHistorico();
  if (lista.length === 0) { container.innerHTML = ''; return; }

  container.innerHTML = `
    <div class="vcep-historico-label">Verificados recentemente</div>
    <div class="vcep-historico-chips">
      ${lista.map(h => `
        <button type="button" class="vcep-chip-historico" onclick="_vcepReverificarHistorico('${h.cep}')" title="${esc(h.endereco)}">
          ${esc(formatCEP(h.cep))}
        </button>`).join('')}
    </div>`;
}

function _vcepReverificarHistorico(cep) {
  const linhaEnd = document.getElementById('linha-busca-endereco');
  if (linhaEnd.style.display !== 'none') alternarModoBusca();
  document.getElementById('verificar-cep-input').value = formatCEP(cep);
  verificarCEP();
}

// ===== COMPARAR DOIS CEPs LADO A LADO =====
function alternarComparar() {
  const linha = document.getElementById('linha-comparar');
  const aberto = linha.style.display !== 'none';
  linha.style.display = aberto ? 'none' : 'flex';
  if (!aberto) setTimeout(() => document.getElementById('verificar-cep-input-b')?.focus(), 60);
}

function _vcepEsconderComparacao() {
  const linha = document.getElementById('linha-comparar');
  if (linha) linha.style.display = 'none';
}

async function verificarComparar() {
  const cepA = (document.getElementById('verificar-cep-input').value || '').replace(/\D/g, '');
  const cepB = (document.getElementById('verificar-cep-input-b').value || '').replace(/\D/g, '');

  if (cepA.length !== 8 || cepB.length !== 8) {
    toast('Informe os dois CEPs (8 dígitos cada) pra comparar', 'error');
    return;
  }

  const resultado = document.getElementById('verificar-resultado');
  resultado.innerHTML = `<div class="loading-row" style="padding:30px;text-align:center;"><div class="spinner"></div></div>`;

  try {
    const [ra, rb] = await Promise.all([
      api('/verificar-cep', { method: 'POST', body: JSON.stringify({ cep: cepA }) }),
      api('/verificar-cep', { method: 'POST', body: JSON.stringify({ cep: cepB }) }),
    ]);
    _vcepSalvarHistorico(cepA, ra.endereco);
    _vcepSalvarHistorico(cepB, rb.endereco);

    resultado.innerHTML = `
      <div class="vcep-comparar-grid">
        <div class="vcep-comparar-col">
          <div class="vcep-comparar-titulo">${esc(formatCEP(cepA))}<span>${esc(ra.endereco || '')}</span></div>
          ${_vcepAnalise(ra, 'a-', false)}
        </div>
        <div class="vcep-comparar-col">
          <div class="vcep-comparar-titulo">${esc(formatCEP(cepB))}<span>${esc(rb.endereco || '')}</span></div>
          ${_vcepAnalise(rb, 'b-', false)}
        </div>
      </div>`;
  } catch (e) {
    resultado.innerHTML = `<div class="vcep-erro">${esc(e.message)}</div>`;
  }
}

function _renderVcep(container, r) {
  const endCurto = r.endereco ? r.endereco.split(',').slice(0, 2).join(',') : '—';
  container.innerHTML = `
    <div class="vcep-geo">
      <div class="vcep-geo-pin">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#E6F1FB" stroke-width="2.5">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
      </div>
      <div class="vcep-geo-info">
        <div class="vcep-geo-addr">${esc(endCurto)}</div>
        <div class="vcep-geo-chips">
          <span class="vcep-chip vcep-chip-zona">${esc(ZONA_LABEL[r.zona] || r.zona)}</span>
          <span class="vcep-chip vcep-chip-cep">${esc(formatCEP(r.cep))}</span>
        </div>
      </div>
    </div>
    <div class="vcep-tabs" id="vcep-tabs">
      <button class="vcep-tab active" id="vtab-analise" onclick="vcepSwitchTab('analise')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Análise
      </button>
      <button class="vcep-tab" id="vtab-add" onclick="vcepSwitchTab('add')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Adicionar
      </button>
      <button class="vcep-tab" id="vtab-novo" onclick="vcepSwitchTab('novo')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="12" y1="10" x2="12" y2="16"/><line x1="9" y1="13" x2="15" y2="13"/></svg>
        Novo dia
      </button>
    </div>
    <div class="vcep-painel" id="vcep-painel"></div>`;
  _vcepRenderTab(r);
}

function vcepSwitchTab(tab) {
  vcepTabAtual = tab;
  ['analise','add','novo'].forEach(t => {
    document.getElementById('vtab-' + t)?.classList.toggle('active', t === tab);
  });
  _vcepRenderTab(verificacaoAtual);
}

function _vcepRenderTab(r) {
  const painel = document.getElementById('vcep-painel');
  if (!painel || !r) return;

  // A caixa alarga só na aba de análise (a dos mapas). Nas outras — Adicionar
  // e Novo dia — volta aos 640px centrados, que é o certo para formulário.
  const caixa = painel.closest('.verificador-box--full');
  if (caixa) caixa.classList.toggle('vcep-modo-mapas', vcepTabAtual === 'analise');

  if (vcepTabAtual === 'analise') painel.innerHTML = _vcepAnalise(r);
  if (vcepTabAtual === 'add')     painel.innerHTML = _vcepAdd(r);
  if (vcepTabAtual === 'novo')    painel.innerHTML = _vcepNovoDia(r);

  // O mapa só existe na aba de análise, e precisa ser montado DEPOIS do
  // innerHTML — o container é criado ali dentro.
  if (vcepTabAtual === 'analise') vcepRenderizarMapa(r);

  if (vcepTabAtual === 'analise' && vcepExpandido !== null) _vcepExpandir(vcepExpandido, r);

  if (vcepTabAtual === 'add' || vcepTabAtual === 'novo') {
    document.querySelectorAll('.vcep-dpill').forEach(p => {
      p.addEventListener('click', () => {
        document.querySelectorAll('.vcep-dpill').forEach(x => x.classList.remove('sel'));
        p.classList.add('sel');
      });
    });
  }

  // Preenche o select de setor da aba Adicionar. Se os setores ainda não
  // vieram (usuário rápido logo após abrir o painel), busca e então preenche —
  // por isso o select nasce como "Carregando setores..." e não vazio.
  if (vcepTabAtual === 'add') {
    if (setores.length) {
      preencherSelectSetor('vadd-setor');
    } else {
      carregarSetores().then(() => preencherSelectSetor('vadd-setor'));
    }
  }
}

function _vcepAnalise(r, prefixo = '', interativo = true) {
  if (!r.sugestoes || r.sugestoes.length === 0) {
    return `<div class="vcep-empty"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><p>Nenhuma rota cadastrada.<br>Use "Novo dia" para criar a primeira.</p></div>`;
  }

  const monta = (s, i) => {
    const encaixe = _encaixeInfo(s);
    const dataTxt = s.data_referencia ? ' · ' + formatarData(s.data_referencia) : '';
    const ptsTxt  = s.vazia ? 'rota vazia' : `${s.total_pontos} pts`;

    const idCard = `vcep-rc-${prefixo}${i}`;
    const idDet  = `vcep-det-${prefixo}${i}`;
    const larguraBarra = Math.min(100, Math.round((s.score / ESCALA_BARRA) * 100));

    // Os motivos vêm prontos do servidor e substituem o número solto: o score
    // é uma soma sem unidade nem teto, "87" não diz nada. "3 dos 8 pontos na
    // zona leste · 2,1 km do mais próximo" diz tudo.
    const motivos = (s.motivos || []).map(m =>
      `<span class="vcep-motivo">${esc(m)}</span>`).join('');

    return `
      <div class="vcep-rota-card vcep-card-${encaixe.classe}" id="${idCard}"
           data-indice="${i}"
           ${interativo ? `onmouseenter="vcepDestacarNoMapa(${i})" onmouseleave="vcepDestacarNoMapa(null)"` : ''}
           ${interativo ? `onclick="vcepToggleCard('${prefixo}',${i})"` : ''}>
        <div class="vcep-rota-inner">
          <div class="vcep-avatar" style="background:rgba(${_hexRgb(s.tecnico_cor)},.13);color:${escCor(s.tecnico_cor)}">
            ${esc(_ini(s.tecnico_nome))}
            <span class="vcep-avatar-rank">${i + 1}</span>
          </div>
          <div class="vcep-rota-info">
            <div class="vcep-rota-nome">
              ${esc(s.tecnico_nome)}
              ${s.lotada ? `<span class="vcep-tag-lotada" title="Acima da capacidade ideal">${icone('alerta', 'icone-10')} cheia</span>` : ''}
            </div>
            <div class="vcep-rota-dia">${esc(s.dia_semana)} · ${ptsTxt}${esc(dataTxt)}</div>
            <div class="vcep-motivos">${motivos}</div>
          </div>
          <div class="vcep-rota-score">
            <div class="vcep-veredito" style="color:${encaixe.cor}">${esc(encaixe.texto)}</div>
            <div class="vcep-score-bar"><div class="vcep-score-fill" style="width:${larguraBarra}%;background:${encaixe.cor}"></div></div>
            <div class="vcep-score-num" title="Pontuação interna do cálculo de encaixe">${Math.round(s.score)}</div>
          </div>
          ${interativo ? `
          <button type="button" class="vcep-btn-add-rapido" title="Adicionar este CEP nessa rota"
                  onclick="event.stopPropagation(); vcepSelecionarRota(${s.ficha_id})">
            ${icone('plus', 'icone-13')}
          </button>` : ''}
        </div>
        ${interativo ? `<div class="vcep-rota-detalhe" id="${idDet}" style="display:none"></div>` : ''}
      </div>`;
  };

  // Separa o que serve do que não serve. Antes as 10 rotas vinham numa lista
  // só, com o mesmo peso visual — e a decisão ficava por conta do usuário
  // comparar números. "Fora de mão" quase nunca interessa, então vai recolhido.
  // AGRUPA POR TÉCNICO. Antes as rotas de todo mundo vinham numa lista só e
  // ficava confuso saber de quem era cada dia (pedido do Kalebe em 2026-08-20:
  // "tudo em um lugar só está confuso, separar por técnico"). A régua é a
  // mesma — as que servem em cima, as "fora de mão" recolhidas — só que agora
  // dentro de cada técnico.
  //
  // O índice ORIGINAL (i) é preservado em cada card: o mapa, o clique de
  // simulação e o expandir dependem dele. Reindexar aqui quebraria os três.
  const porTecnico = new Map();
  r.sugestoes.forEach((s, i) => {
    const chave = s.tecnico_id ?? s.tecnico_nome ?? 'sem';
    if (!porTecnico.has(chave)) {
      porTecnico.set(chave, {
        chave, nome: s.tecnico_nome || 'Sem técnico', cor: s.tecnico_cor,
        servem: [], naoServem: [], melhorScore: -Infinity, indices: [],
      });
    }
    const g = porTecnico.get(chave);
    g.indices.push(i);
    const fora = s.classificacao === 'fora' && !s.vazia;
    (fora ? g.naoServem : g.servem).push(monta(s, i));
    if (!fora) g.melhorScore = Math.max(g.melhorScore, s.score || 0);
  });

  // Técnico com melhor encaixe primeiro: é onde o olho deve ir.
  const grupos = [...porTecnico.values()].sort((a, b) => b.melhorScore - a.melhorScore);

  // Registra, para cada sugestão, a qual GRUPO (posição na lista) ela pertence.
  // É esse mapa que o destaque e a simulação usam para achar o mapa certo.
  vcepIndiceGrupo = {};
  grupos.forEach((g, gi) => g.indices.forEach(i => { vcepIndiceGrupo[i] = gi; }));

  const nenhumServe = grupos.every(g => g.servem.length === 0);
  const alerta = nenhumServe ? `
    <div class="vcep-alerta-nenhuma">
      ${icone('alerta', 'icone-13')}
      <div>
        <strong>Nenhuma rota atual atende bem esse endereço.</strong><br>
        Todas ficam fora de mão. Considere criar um novo dia na aba "Novo dia"
        em vez de forçar o encaixe.
      </div>
    </div>` : '';

  const blocos = grupos.map((g, gi) => {
    const foraId = 'vcep-fora-g' + gi;
    const recolhidas = g.naoServem.length ? `
      <button type="button" class="vcep-toggle-fora" onclick="vcepAlternarFora(this)">
        Mostrar ${g.naoServem.length} rota${g.naoServem.length !== 1 ? 's' : ''} fora de mão
      </button>
      <div class="vcep-fora-lista" id="${foraId}" style="display:none;">${g.naoServem.join('')}</div>` : '';

    const corpo = g.servem.length
      ? g.servem.join('')
      : (g.naoServem.length
          ? '<div class="vcep-grupo-vazio">Nenhum dia deste técnico encaixa bem — só fora de mão.</div>'
          : '<div class="vcep-grupo-vazio">Sem rotas em aberto.</div>');

    // Cada técnico: seu próprio mapa e sua própria barra de simulação, com o
    // sufixo do grupo (g{gi}) que amarra ao vcepMapasGrupo[gi].
    return `
      <div class="vcep-grupo-tec">
        <div class="vcep-grupo-cab" style="--cor:${escCor(g.cor)}">
          <span class="vcep-grupo-bolinha" style="background:${escCor(g.cor)}"></span>
          <span class="vcep-grupo-nome">${esc(g.nome)}</span>
          <span class="vcep-grupo-cont">${g.servem.length} que ${g.servem.length === 1 ? 'serve' : 'servem'}</span>
        </div>
        <div id="vcep-mapa-g${gi}" class="vcep-mapa"></div>
        <div id="vcep-sim-g${gi}" class="vcep-sim-barra">
          <span class="vcep-sim-dica">Clique num dia para ver como a rota ficaria.</span>
        </div>
        ${corpo}
        ${recolhidas}
      </div>`;
  }).join('');

  // Os blocos vão numa GRADE: com dois técnicos, um mapa ao lado do outro (a
  // tela tem largura para isso); com três ou mais, quebra em linhas. Um só
  // técnico ocupa a largura inteira.
  return `<div class="vcep-analise-wrap">
    ${alerta}
    <div class="vcep-grupos-grade">${blocos}</div>
  </div>`;
}

// ─── Mapa do verificador de encaixe ─────────────────────────────────────
// O número respondia "quanto encaixa". O mapa responde "onde", que é a
// pergunta que a cabeça faz primeiro. Ver o CEP caindo no meio do aglomerado
// de segunda do Pedro decide a questão sem ler nada.
// UM MAPA POR TÉCNICO (pedido do Kalebe em 2026-08-20). Antes era um mapa só
// com as rotas de todos sobrepostas. Agora cada técnico tem o seu, dentro do
// bloco dele — os índices abaixo é que amarram tudo:
//   vcepMapasGrupo[g]  = { mapa, alvoMarker, camadaSim }  — um por grupo
//   vcepCamadas[i]     = { camada, cor, grupo }           — um por sugestão
//   vcepIndiceGrupo[i] = g   — de qual grupo é a sugestão i
// O índice GLOBAL i é preservado porque o destaque e a simulação chegam por
// ele; reindexar quebraria os dois.
let vcepMapasGrupo = [];
let vcepCamadas = [];
let vcepIndiceGrupo = {};

function vcepRenderizarMapa(r) {
  try {
    _vcepDesenharMapas(r);
  } catch (e) {
    // O mapa é apoio à decisão, não a decisão. Se ele falhar, a análise em
    // texto — que é a informação essencial — não pode cair junto.
    console.error('Falha ao desenhar os mapas de encaixe:', e);
    document.querySelectorAll('.vcep-mapa').forEach(el => { el.style.display = 'none'; });
  }
}

// Um mapa POR TÉCNICO. Cada mapa mostra só as rotas daquele técnico + o mesmo
// alvo (o endereço consultado), para o técnico ser comparado no seu próprio
// contexto, sem as rotas do outro poluindo.
function _vcepDesenharMapas(r) {
  if (!r || typeof L === 'undefined') return;
  if (!Number.isFinite(r.lat) || !Number.isFinite(r.lng)) return;

  // Destrói os mapas da consulta anterior: o Leaflet guarda estado no elemento
  // e recriar sem destruir deixa o mapa cinza.
  vcepMapasGrupo.forEach(m => { if (m && m.mapa) m.mapa.remove(); });
  vcepMapasGrupo = [];
  vcepCamadas = [];

  const valida = (p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng);

  // Agrupa os índices das sugestões por grupo (a mesma divisão da tela).
  const porGrupo = {};
  (r.sugestoes || []).forEach((s, i) => {
    const g = vcepIndiceGrupo[i];
    if (g === undefined) return;
    (porGrupo[g] = porGrupo[g] || []).push(i);
  });

  Object.keys(porGrupo).forEach(gStr => {
    const gi = Number(gStr);
    const el = document.getElementById(`vcep-mapa-g${gi}`);
    if (!el) return;

    // setView junto da criação, antes de qualquer camada — sem visão definida,
    // o primeiro circleMarker estoura em "reading 'intersects'".
    const mapa = L.map(el, { scrollWheelZoom: false, attributionControl: false })
                  .setView([r.lat, r.lng], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(mapa);

    const limites = [[r.lat, r.lng]];

    porGrupo[gi].forEach(i => {
      const s = r.sugestoes[i];
      const camada = L.layerGroup().addTo(mapa);
      const cor = s.tecnico_cor || '#4f8dfb';
      const fraca = s.classificacao === 'fora' && !s.vazia;

      (s.pontos || []).filter(valida).forEach(p => {
        L.circleMarker([p.lat, p.lng], {
          radius: fraca ? 3 : 5, color: cor, fillColor: cor,
          fillOpacity: fraca ? 0.25 : 0.85, weight: fraca ? 1 : 2,
          opacity: fraca ? 0.3 : 0.9,
        }).addTo(camada);
        if (!fraca) limites.push([p.lat, p.lng]);
      });

      // A linha até o ponto mais próximo torna "2,1 km fora da rota" algo que
      // se enxerga em vez de um número para acreditar.
      if (valida(s.ponto_proximo) && !fraca) {
        L.polyline([[r.lat, r.lng], [s.ponto_proximo.lat, s.ponto_proximo.lng]], {
          color: cor, weight: 2, opacity: 0.5, dashArray: '4,6',
        }).addTo(camada);
      }

      vcepCamadas[i] = { camada, cor, grupo: gi };
    });

    // O alvo vai por último e é visualmente diferente — é a pergunta, não uma
    // das respostas. Repetido em cada mapa de propósito: é a referência comum.
    const alvoMarker = L.circleMarker([r.lat, r.lng], {
      radius: 9, color: '#fff', fillColor: '#e02020', fillOpacity: 1, weight: 3,
    }).addTo(mapa).bindTooltip(r.endereco || r.cep || 'Endereço consultado',
                              { direction: 'top' });

    if (limites.length > 1) {
      const caixa = L.latLngBounds(limites);
      if (caixa.isValid()) mapa.fitBounds(caixa.pad(0.2));
    }

    vcepMapasGrupo[gi] = { mapa, alvoMarker, camadaSim: null };

    // O container nasce escondido dentro da aba; sem invalidateSize o Leaflet
    // calcula tamanho zero e o mapa aparece cortado.
    setTimeout(() => { if (vcepMapasGrupo[gi]) vcepMapasGrupo[gi].mapa.invalidateSize(); }, 120);
  });
}

// Passar o mouse no card acende a rota correspondente no mapa. É o que liga
// as duas metades da tela: sem isso são duas listas que não se conversam.
function vcepDestacarNoMapa(indice) {
  // Só apaga as OUTRAS rotas do MESMO mapa (mesmo técnico). Antes, com um mapa
  // só, apagava tudo; agora cada técnico é destacado no seu próprio mapa.
  const grupoAlvo = indice === null ? null : vcepIndiceGrupo[indice];
  vcepCamadas.forEach((c, i) => {
    if (!c) return;
    // Card de um técnico não mexe no mapa do outro.
    if (grupoAlvo !== null && c.grupo !== grupoAlvo) return;
    const apagar = indice !== null && i !== indice;
    c.camada.eachLayer(l => {
      if (l.setStyle) l.setStyle({ opacity: apagar ? 0.12 : 0.9, fillOpacity: apagar ? 0.08 : 0.85 });
    });
  });
}

// ─── Simulação: como o dia fica se este endereço entrar ─────────────────
// Clicar no dia deixa de ser só "expandir detalhe" e passa a desenhar o
// trajeto inteiro na ordem em que o técnico vai rodar, com o ponto novo já
// no lugar que o otimizador daria a ele. A pergunta que isso responde não é
// "encaixa?", é "encaixa ONDE, e me custa quanto?".

async function vcepSimularNoMapa(indice) {
  const r = verificacaoAtual;
  if (!r) return;
  const s = r.sugestoes?.[indice];
  if (!s) return;

  // A simulação acontece NO MAPA DO TÉCNICO daquele dia.
  const gi = vcepIndiceGrupo[indice];
  const grupo = vcepMapasGrupo[gi];
  if (!grupo || !grupo.mapa) return;
  const mapaTec = grupo.mapa;

  const barra = document.getElementById(`vcep-sim-g${gi}`);
  if (barra) barra.innerHTML = `<span class="vcep-sim-carregando">Calculando como o dia ${esc(s.dia_semana)} ficaria...</span>`;

  let sim;
  try {
    sim = await api(`/fichas/${s.ficha_id}/simular-encaixe`, {
      method: 'POST',
      body: JSON.stringify({ lat: r.lat, lng: r.lng, endereco: r.endereco || r.cep }),
    });
  } catch (e) {
    if (barra) barra.innerHTML = `<span class="vcep-sim-erro">${esc(e.message)}</span>`;
    return;
  }

  // Limpa só a camada de simulação DESTE mapa — os pontos das outras rotas
  // continuam, senão o usuário perde a noção de onde tudo está.
  if (grupo.camadaSim) { grupo.camadaSim.remove(); }
  grupo.camadaSim = L.layerGroup().addTo(mapaTec);
  const vcepCamadaSimulacao = grupo.camadaSim;

  const cor = s.tecnico_cor || '#4f8dfb';
  const caminho = [];

  if (Number.isFinite(sim.partida?.lat)) {
    caminho.push([sim.partida.lat, sim.partida.lng]);
    L.marker([sim.partida.lat, sim.partida.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="vcep-pin-base">${icone('casa', 'icone-12')}</div>`,
        iconSize: [26, 26], iconAnchor: [13, 13],
      }),
    }).addTo(vcepCamadaSimulacao).bindTooltip('Partida: ' + (sim.partida.endereco || ''), { direction: 'top' });
  }

  (sim.depois?.sequencia || []).forEach((p) => {
    caminho.push([p.lat, p.lng]);
    // O ponto novo entra visualmente diferente: é a única parada que ainda
    // não existe, e o senso da simulação é justamente ver onde ela cai.
    L.marker([p.lat, p.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="vcep-pin-parada${p.novo ? ' novo' : ''}"
                    style="${p.novo ? '' : `background:${escCor(cor)}`}">${p.posicao}</div>`,
        iconSize: [24, 24], iconAnchor: [12, 12],
      }),
      zIndexOffset: p.novo ? 1000 : 0,
    }).addTo(vcepCamadaSimulacao)
      .bindTooltip(`${p.posicao}. ${esc(p.cliente)}`, { direction: 'top' });
  });

  if (caminho.length > 1) {
    L.polyline(caminho, { color: cor, weight: 3, opacity: 0.85 }).addTo(vcepCamadaSimulacao);
  }

  const caixa = L.latLngBounds(caminho);
  if (caixa.isValid()) mapaTec.fitBounds(caixa.pad(0.15));

  if (barra) barra.innerHTML = _vcepResumoSimulacao(sim, s);
}

function _vcepResumoSimulacao(sim, s) {
  if (sim.rota_vazia) {
    return `<div class="vcep-sim-resumo">
      <strong>${esc(s.dia_semana)}</strong> — rota vazia. Este seria o primeiro
      ponto do dia: <strong>${fmtKm(sim.depois.km)} km</strong> saindo da base.
    </div>`;
  }

  const km = sim.acrescimo_km;
  const min = sim.acrescimo_min;
  // Custo por parada é o que deixa a comparação entre dias justa: 4 km num dia
  // de 2 pontos pesa muito mais do que 4 km num dia de 8.
  const barato = km <= 3;

  return `<div class="vcep-sim-resumo">
    <div class="vcep-sim-linha">
      <strong>${esc(s.dia_semana)}</strong>
      <span class="vcep-sim-pos">entra como parada ${sim.posicao_novo} de ${sim.depois.paradas}</span>
    </div>
    <div class="vcep-sim-numeros">
      <span>${fmtKm(sim.antes.km)} km <span class="vcep-sim-seta">→</span> <strong>${fmtKm(sim.depois.km)} km</strong></span>
      <span class="vcep-sim-delta ${barato ? 'ok' : 'caro'}">
        +${fmtKm(km)} km · +${min} min
      </span>
    </div>
  </div>`;
}

function vcepAlternarFora(btn) {
  const lista = btn.nextElementSibling;
  const escondida = lista.style.display === 'none';
  lista.style.display = escondida ? '' : 'none';
  btn.classList.toggle('aberto', escondida);
}

function vcepToggleCard(prefixo, i) {
  // prefixo só é diferente de '' no modo comparar — que é somente
  // leitura e nem chama isso (evita ids duplicados entre as 2 colunas).
  if (vcepExpandido === i) {
    vcepExpandido = null;
    document.getElementById('vcep-det-' + prefixo + i)?.style.setProperty('display', 'none');
    document.getElementById('vcep-rc-' + prefixo + i)?.classList.remove('vcep-rota-expanded');
    // Fechar o card também limpa a simulação do mapa DAQUELE técnico: deixar o
    // trajeto desenhado sem dia selecionado mostraria uma rota que não responde
    // a pergunta nenhuma.
    const giFechar = vcepIndiceGrupo[i];
    const grpFechar = vcepMapasGrupo[giFechar];
    if (grpFechar && grpFechar.camadaSim) { grpFechar.camadaSim.remove(); grpFechar.camadaSim = null; }
    const barra = document.getElementById(`vcep-sim-g${giFechar}`);
    if (barra) barra.innerHTML = `<span class="vcep-sim-dica">Clique num dia para ver como a rota ficaria.</span>`;
    return;
  }
  if (vcepExpandido !== null) {
    document.getElementById('vcep-det-' + prefixo + vcepExpandido)?.style.setProperty('display', 'none');
    document.getElementById('vcep-rc-' + prefixo + vcepExpandido)?.classList.remove('vcep-rota-expanded');
  }
  vcepExpandido = i;
  _vcepExpandir(i, verificacaoAtual, prefixo);
  // Sem await: o detalhe em texto abre na hora e a simulação (que bate no
  // servidor) preenche a barra quando chegar. Esperar deixaria o clique com
  // uma lentidão que não precisa existir.
  vcepSimularNoMapa(i);
}

function _vcepExpandir(i, r, prefixo = '') {
  const s = r?.sugestoes?.[i];
  const el = document.getElementById('vcep-det-' + prefixo + i);
  const card = document.getElementById('vcep-rc-' + prefixo + i);
  if (!el || !s) return;

  card?.classList.add('vcep-rota-expanded');
  const icones = { pos: icone('check', 'icone-12'), neu: icone('minus', 'icone-12'), neg: icone('x', 'icone-12') };

  const motHtml = _motivos(s, i).map(m => `
    <div class="vcep-motivo-item vcep-motivo-item-${m.tipo}">
      <div class="vcep-motivo-icon vcep-motivo-icon-${m.tipo}">${icones[m.tipo]}</div>
      <div>
        <div class="vcep-motivo-titulo">${esc(m.titulo)}</div>
        <div class="vcep-motivo-desc">${esc(m.desc)}</div>
      </div>
    </div>`).join('');

  el.innerHTML = `
    <div class="vcep-detalhe-body">
      <div class="vcep-detalhe-titulo">Por que essa pontuação?</div>
      <div class="vcep-motivos-detalhe">${motHtml}</div>
      <div class="vcep-metricas">
        <div class="vcep-metrica"><div class="vcep-met-val">${fmtKm(s.dist_minima)}</div><div class="vcep-met-lbl">km do mais próximo</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.pontos_mesma_zona}</div><div class="vcep-met-lbl">pts mesma zona</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.total_pontos || 0}</div><div class="vcep-met-lbl">atendimentos no total</div></div>
      </div>
      <button class="vcep-btn-add" onclick="event.stopPropagation();vcepSelecionarRota(${s.ficha_id})">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Adicionar CEP a essa rota
      </button>
    </div>`;
  el.style.display = 'block';
}

function vcepSelecionarRota(fichaId) {
  vcepSwitchTab('add');
  const sel = document.getElementById('vcep-rota-sel');
  if (sel) sel.value = String(fichaId);
}

function _vcepAdd(r) {
  if (!r.sugestoes || r.sugestoes.length === 0) {
    return `<div class="vcep-empty"><p>Nenhuma rota disponível.<br>Crie um novo dia primeiro.</p></div>`;
  }

  const cepFmt = formatCEP(r.cep || '');
  const opts = r.sugestoes.map(s =>
    `<option value="${s.ficha_id}">${esc(s.tecnico_nome)} — ${esc(s.dia_semana)} (score ${Math.round(s.score)})</option>`
  ).join('');

  return `
    <div class="vcep-form">
      <div class="vcep-form-titulo">Adicionar ${esc(cepFmt)} a uma rota existente</div>
      <div class="vcep-form-grid">
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">CEP</label>
          <input class="vcep-input" type="text" id="vadd-cep" value="${esc(cepFmt)}" style="font-family:var(--font-mono);letter-spacing:1px">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Número</label>
          <input class="vcep-input" type="text" id="vadd-num" placeholder="Ex: 42">
        </div>
        <div class="vcep-fg vcep-fg-full">
          <label class="vcep-lbl">Rota de destino</label>
          <select class="vcep-select" id="vcep-rota-sel">${opts}</select>
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Cliente</label>
          <input class="vcep-input" type="text" id="vadd-cli" placeholder="Nome do cliente">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Telefone *</label>
          <input class="vcep-input" type="tel" id="vadd-telefone" placeholder="(11) 99999-9999"
                 inputmode="numeric" oninput="formatarTelefone(this)">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Tipo de Aparelho</label>
          <select class="vcep-select" id="vadd-tipo">
            <option value="">Selecione...</option>
            <option>Geladeira</option>
            <option>Freezer</option>
            <option>Máquina de Lavar</option>
            <option>Lava e Seca</option>
            <option>Fogão</option>
            <option>Micro-ondas</option>
            <option>Purificador</option>
            <option>Side by Side</option>
            <option>Câmara Fria</option>
            <option>Expositora</option>
            <option>Secadora</option>
            <option>Outro</option>
          </select>
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Modelo</label>
          <input class="vcep-input" type="text" id="vadd-modelo" placeholder="Ex: BRM45">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Setor / Marca *</label>
          <!-- Opções preenchidas por preencherSelectSetor DEPOIS de inserir o
               HTML (ver _vcepRenderTab): montar inline aqui deixava o select
               vazio quando os setores ainda não tinham carregado. -->
          <select class="vcep-select" id="vadd-setor">
            <option value="">Carregando setores...</option>
          </select>
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Nº da OS (DigiTeam)</label>
          <input class="vcep-input" type="text" id="vadd-os" placeholder="Ex: 1208202621026">
        </div>
        <div class="vcep-fg vcep-fg-full">
          <label class="vcep-lbl">Descrição</label>
          <input class="vcep-input" type="text" id="vadd-desc" placeholder="Ex: não gela">
        </div>
      </div>
      <button class="vcep-btn-primary" id="vcep-btn-add-svc" onclick="vcepAdicionarServico()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        Adicionar ponto + otimizar rota
      </button>
    </div>`;
}

function _vcepNovoDia(r) {
  const cepFmt = formatCEP(r.cep || '');
  const tOpts = (r.tecnicos || []).map(t => `<option value="${t.id}">${esc(t.nome)}</option>`).join('');
  const dPills = DIAS_SEMANA_FULL.map(d =>
    `<button type="button" class="vcep-dpill" data-dia="${esc(d)}">${DIAS_ABREV[d]}</button>`
  ).join('');

  const aviso = !r.tem_boa_opcao
    ? `<div class="vcep-aviso">Nenhuma rota tem bom encaixe para ${esc(ZONA_LABEL[r.zona] || r.zona)}. Criar um dia dedicado melhora a eficiência da região.</div>`
    : '';

  return `
    <div class="vcep-form">
      <div class="vcep-form-titulo">Criar novo dia e adicionar ${esc(cepFmt)}</div>
      ${aviso}
      <div class="vcep-form-grid">
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Técnico</label>
          <select class="vcep-select" id="vnovo-tec">${tOpts}</select>
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Data (opcional)</label>
          <input class="vcep-input" type="date" id="vnovo-data">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">CEP de partida</label>
          <input class="vcep-input" type="text" id="vnovo-cep" placeholder="01310-100" maxlength="9" style="font-family:var(--font-mono)" oninput="formatarCEP(this)">
        </div>
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">Nome da base</label>
          <input class="vcep-input" type="text" id="vnovo-base" placeholder="Ex: Portotec Sede">
        </div>
      </div>
      <label class="vcep-lbl">Dia da semana</label>
      <div class="vcep-dias" id="vcep-dias-novo">${dPills}</div>
      <button class="vcep-btn-primary" onclick="vcepCriarNovoDia()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Criar dia + adicionar ${esc(cepFmt)}
      </button>
    </div>`;
}

async function vcepAdicionarServico() {
  if (!verificacaoAtual) return;

  const fichaId = document.getElementById('vcep-rota-sel')?.value;
  const cep = document.getElementById('vadd-cep')?.value;
  if (!fichaId || !cep) { toast('Preencha os campos obrigatórios', 'error'); return; }

  // Setor é obrigatório no servidor (é a "marca": Panasonic, Philco, Loja...).
  // Barrar aqui evita a viagem de ida e volta só para levar o erro de volta.
  const setorId = document.getElementById('vadd-setor')?.value;
  if (!setorId) {
    toast('Escolha o setor/marca do atendimento.', 'error');
    document.getElementById('vadd-setor')?.focus();
    return;
  }

  const telefone = document.getElementById('vadd-telefone')?.value.trim();
  if (!telefone) {
    toast('Informe o telefone do cliente.', 'error');
    document.getElementById('vadd-telefone')?.focus();
    return;
  }

  const btn = document.getElementById('vcep-btn-add-svc');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Geocodificando...'; }

  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep: cep.replace(/\D/g, ''),
        numero:        document.getElementById('vadd-num')?.value || '',
        cliente:       document.getElementById('vadd-cli')?.value || '',
        telefone,
        descricao:     document.getElementById('vadd-desc')?.value || '',
        tipo_aparelho: document.getElementById('vadd-tipo')?.value || '',
        modelo:        document.getElementById('vadd-modelo')?.value || '',
        numero_os:     document.getElementById('vadd-os')?.value || '',
        setor_id:      setorId,
      }),
    });

    lembrarSetor(setorId);
    toast(`Atendimento adicionado! ${fmtKm(r.distancia_total)} km`, 'success');
    if (r.aviso) toast(r.aviso, 'info');

    mostrarDetalhe();

    await renderFichaDetalhe(parseInt(fichaId, 10));
    await carregarTecnicos();
    document.getElementById('verificar-resultado').innerHTML = '';
    document.getElementById('verificar-cep-input').value = '';

  } catch (e) {
    toast(e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = 'Adicionar atendimento + otimizar rota'; }
  }
}

async function vcepCriarNovoDia() {
  if (!verificacaoAtual) return;

  const tecnicoSelect  = document.getElementById('vnovo-tec');
  const diaSelecionado = document.querySelector('#vcep-dias-novo .vcep-dpill.sel');
  const cepPartida     = (document.getElementById('vnovo-cep')?.value || '').replace(/\D/g, '');

  if (!tecnicoSelect?.value) { toast('Selecione um técnico', 'error'); return; }
  if (!diaSelecionado)       { toast('Selecione um dia da semana', 'error'); return; }
  if (cepPartida && cepPartida.length !== 8) {
    toast('CEP de partida incompleto', 'error'); return;
  }
  if (!cepPartida &&
      !confirm('Sem CEP de partida a rota não pode ser otimizada. Criar mesmo assim?')) {
    return;
  }

  const body = {
    tecnico_id:        parseInt(tecnicoSelect.value, 10),
    dia_semana:        diaSelecionado.dataset.dia,
    data_referencia:   document.getElementById('vnovo-data')?.value || '',
    ponto_partida:     document.getElementById('vnovo-base')?.value || '',
    ponto_partida_cep: cepPartida,
  };

  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify(body) });
    toast(`Ficha "${body.dia_semana}" criada!`, 'success');
    if (r.aviso) toast(r.aviso, 'info');

    await carregarTecnicos();
    mostrarDetalhe();
    await renderFichaDetalhe(r.id);

    document.getElementById('add-ficha-id').value  = r.id;
    document.getElementById('add-cep').value       = formatCEP(verificacaoAtual.cep);
    document.getElementById('add-numero').value    = '';
    document.getElementById('add-cliente').value   = '';
    document.getElementById('add-descricao').value = '';
    document.getElementById('modal-add-servico').classList.add('open');
    setTimeout(() => document.getElementById('add-numero').focus(), 150);

  } catch (e) { toast(e.message, 'error'); }
}

async function criarFicha() {
  const dia = document.getElementById('nova-dia').value;
  const tecnicoId = document.getElementById('nova-ficha-tecnico-id').value;
  const cepPartida = document.getElementById('nova-partida-cep').value.replace(/\D/g, '');

  if (!dia) { toast('Selecione um dia da semana', 'error'); return; }
  if (cepPartida && cepPartida.length !== 8) { toast('CEP de partida incompleto', 'error'); return; }

  const body = {
    tecnico_id:        parseInt(tecnicoId, 10),
    dia_semana:        dia,
    data_referencia:   document.getElementById('nova-data').value,
    ponto_partida:     document.getElementById('nova-partida-nome').value,
    ponto_partida_cep: cepPartida,
  };

  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify(body) });
    fecharModais();
    toast(`Ficha "${dia}" criada!`, 'success');
    if (r.aviso) toast(r.aviso, 'info');
    await carregarTecnicos();
    await selecionarFicha(r.id);
  } catch (e) { toast(e.message, 'error'); }
}

async function corrigirPartidaPadrao() {
  if (!confirm('Preencher com o CEP da loja todas as fichas que estão sem ponto de partida?')) return;

  try {
    const r = await api('/fichas/corrigir-partida-padrao', { method: 'POST' });
    toast(r.mensagem, r.corrigidas > 0 ? 'success' : 'info');
    if (r.corrigidas > 0) await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
}

async function deletarFicha(evt, id) {
  evt.stopPropagation();
  if (!confirm('Remover esta ficha e todos os seus serviços?')) return;

  try {
    await api(`/fichas/${id}`, { method: 'DELETE' });
    if (fichaAtiva?.id === id) mostrarEstadoVazio();
    await carregarTecnicos();
    toast('Ficha removida', 'info');
  } catch (e) { toast(e.message, 'error'); }
}

async function adicionarServico() {
  const fichaId = document.getElementById('add-ficha-id').value;
  const cep = document.getElementById('add-cep').value.replace(/\D/g, '');

  if (cep.length !== 8) { toast('Informe um CEP válido', 'error'); return; }

  // Valida ANTES de travar o botão — as duas checagens têm que vir antes de
  // qualquer `btn.disabled = true`, senão um retorno antecipado aqui deixa o
  // botão preso em "Geocodificando..." pra sempre (o `finally` só cobre o
  // `try` que vem depois; um `return` daqui nunca passa por ele).
  const setorEscolhido = document.getElementById('add-setor').value;
  if (!setorEscolhido) {
    toast('Escolha o setor do atendimento.', 'error');
    document.getElementById('add-setor').focus();
    return;
  }

  const telefone = document.getElementById('add-telefone').value.trim();
  if (!telefone) {
    toast('Informe o telefone do cliente.', 'error');
    document.getElementById('add-telefone').focus();
    return;
  }

  const btn = document.getElementById('btn-add-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Geocodificando...';

  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep,
        numero:        document.getElementById('add-numero').value,
        cliente:       document.getElementById('add-cliente').value,
        telefone,
        descricao:     document.getElementById('add-descricao').value,
        tipo_aparelho: document.getElementById('add-tipo-aparelho').value,
        modelo:        document.getElementById('add-modelo').value,
        numero_os:     document.getElementById('add-numero-os').value,
        setor_id:      setorEscolhido,
      }),
    });

    lembrarSetor(setorEscolhido);

    fecharModais();
    toast(`Atendimento adicionado! Distância estimada: ${fmtKm(r.distancia_total)} km`, 'success');
    if (r.aviso) toast(r.aviso, 'info');

    mostrarDetalhe();
    await renderFichaDetalhe(parseInt(fichaId, 10));
    await carregarTecnicos();

  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Adicionar + Otimizar';
  }
}

async function removerServico(servicoId, fichaId) {
  if (!confirm('Remover este atendimento do roteiro?')) return;

  const row = document.getElementById('svc-' + servicoId);
  if (row) row.style.opacity = '0.4';

  try {
    const r = await api(`/servicos/${servicoId}`, { method: 'DELETE' });
    toast(`Atendimento removido. ${fmtKm(r.distancia_total)} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();
  } catch (e) {
    toast(e.message, 'error');
    if (row) row.style.opacity = '1';
  }
}

async function forcarOtimizacao(fichaId) {
  try {
    const r = await api(`/fichas/${fichaId}/otimizar`, { method: 'POST' });

    if (r.sem_partida) {
      toast('Esta ficha não tem ponto de partida — nada a otimizar.', 'error');
      return;
    }

    let msg = `Rota otimizada! ${fmtKm(r.distancia_total)} km`;
    if (r.ganho_2opt_km > 0.1) msg += ` (−${fmtKm(r.ganho_2opt_km)} km com o 2-opt)`;
    toast(msg, 'success');

    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
}

async function alternarStatusFicha(fichaId, statusAtual) {
  const novoStatus = statusAtual === 'concluida' ? 'pendente' : 'concluida';

  if (novoStatus === 'pendente' && !confirm('Reabrir esta rota como pendente de novo?')) return;

  try {
    const r = await api(`/fichas/${fichaId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status: novoStatus }),
    });
    toast(novoStatus === 'concluida' ? 'Rota marcada como concluída' : 'Rota reaberta', 'success');
    if (r?.planilha) toast(r.planilha, 'info');
    if (r?.aviso) toast(r.aviso, 'error');
    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();

    // Concluiu a rota? oferece dar baixa na planilha de pedidos.
    if (novoStatus === 'concluida') abrirConciliacao(fichaId);
  } catch (e) { toast(e.message, 'error'); }
}

// ─── Conciliação com a planilha de pedidos ──────────────────────────
// Sempre mostra a prévia antes de gravar: mexer na planilha da equipe sem
// avisar é o tipo de coisa que ninguém perdoa se der errado.
async function abrirConciliacao(fichaId) {
  const modal = document.getElementById('modal-conciliacao');
  const corpo = document.getElementById('conciliacao-corpo');
  const btn = document.getElementById('btn-aplicar-conciliacao');

  modal.classList.add('open');
  corpo.innerHTML = `<div class="loading-row" style="justify-content:center;gap:10px;display:flex;padding:20px;"><div class="spinner"></div> Conferindo a planilha...</div>`;
  btn.style.display = 'none';

  let r;
  try {
    r = await api(`/fichas/${fichaId}/conciliar`, { method: 'POST' });
  } catch (e) {
    corpo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const casados = r.casados || [];
  const outros = r.outros || [];

  // Ficha já conciliada: a prévia mentiria (as linhas com baixa são puladas e
  // tudo cairia em "Outros"). Melhor dizer a verdade e não deixar gravar.
  if (r.ja_conciliada) {
    corpo.innerHTML = `
      <div class="conc-alerta" style="margin-top:0;">
        Esta ficha <strong>já foi conciliada</strong> com a planilha. As baixas
        já estão lá.<br><br>
        Se precisar refazer, reabra a rota primeiro — aí as baixas são desfeitas
        e você pode conciliar de novo.
      </div>`;
    btn.style.display = 'none';
    return;
  }

  corpo.innerHTML = `
    <div class="conc-resumo">
      <div class="conc-bloco">
        <div class="conc-num" style="color:var(--success-text)">${casados.length}</div>
        <div class="conc-lbl">com baixa na planilha</div>
      </div>
      <div class="conc-bloco">
        <div class="conc-num" style="color:var(--gold-text)">${outros.length}</div>
        <div class="conc-lbl">vão pra "Outros Atendimentos"</div>
      </div>
    </div>

    ${casados.length ? `
      <div class="conc-titulo">Baixa na planilha</div>
      ${casados.map(c => `
        <div class="conc-item">
          <span class="conc-tag ${c.forca === 'nome+modelo' ? 'ok' : 'aviso'}">
            ${c.forca === 'nome+modelo' ? 'nome + modelo' : 'só o nome'}
          </span>
          <div>
            <div class="conc-cliente">${esc(c.cliente)}</div>
            <div class="conc-meta">linha ${c.linha} · peça: ${esc(c.peca) || '—'}</div>
          </div>
        </div>`).join('')}
    ` : ''}

    ${outros.length ? `
      <div class="conc-titulo">Outros atendimentos (outra marca / vistoria)</div>
      ${outros.map((o, i) => `
        <div class="conc-item">
          <span class="conc-tag neutro">fora da planilha</span>
          <div style="flex:1;min-width:0;">
            <div class="conc-cliente">${esc(o.cliente)}</div>
            <div class="conc-meta">${esc(o.aparelho) || '—'}${o.modelo ? ' · ' + esc(o.modelo) : ''}</div>
            <button class="btn btn-ghost btn-sm" style="margin-top:7px;"
                    onclick="vincularPelaPrevia(${fichaId}, ${i}, this)">
              Tem peça comprada? vincular
            </button>
          </div>
        </div>`).join('')}
    ` : ''}

    ${casados.some(c => c.forca === 'nome') ? `
      <div class="conc-alerta">
        Os marcados como <strong>"só o nome"</strong> casaram pelo cliente, mas o modelo
        não bateu — vão ficar amarelos na planilha pra alguém conferir.
      </div>` : ''}
  `;

  btn.style.display = '';
  btn.disabled = false;
  btn.textContent = `Confirmar (${casados.length} baixa${casados.length !== 1 ? 's' : ''})`;
  btn.onclick = () => aplicarConciliacao(fichaId);

  _conciliacaoOutros = outros;
}

// Guarda os "não casados" da prévia atual, pra poder vincular um deles a uma
// compra sem sair do modal.
let _conciliacaoOutros = [];

// Erro de ordem comum: concluir a rota antes de vincular a peça. Aqui dá pra
// consertar na hora, em vez de descobrir depois que a baixa não aconteceu.
async function vincularPelaPrevia(fichaId, indice, botao) {
  const alvo = _conciliacaoOutros[indice];
  if (!alvo) return;

  botao.disabled = true;
  botao.textContent = 'Buscando compras...';

  let r;
  try {
    r = await api('/pedidos');
  } catch (e) {
    toast(e.message, 'error');
    botao.disabled = false;
    botao.textContent = 'Tem peça comprada? vincular';
    return;
  }

  const pendentes = (r.pedidos || []).filter(p => !p.cliente_final);
  if (pendentes.length === 0) {
    botao.textContent = 'Nenhuma compra sem cliente';
    return;
  }

  const container = botao.parentElement;
  botao.remove();
  const caixa = document.createElement('div');
  caixa.className = 'previa-vinculo';
  caixa.innerHTML = `
    <label class="form-label">Qual compra é do ${esc(alvo.cliente)}?</label>
    <select class="form-input" id="previa-sel-${indice}">
      <option value="">Selecione a compra...</option>
      ${pendentes.map(p => `
        <option value="${p.linha}">${esc(p.valor)} · NF ...${esc((p.nota_fiscal||'').slice(-8))} · ${esc(p.data)}</option>
      `).join('')}
    </select>
    <button class="btn btn-primary btn-sm" style="margin-top:8px;"
            onclick="confirmarVinculoPrevia(${fichaId}, ${indice})">Vincular e refazer prévia</button>
  `;
  container.appendChild(caixa);
}

async function confirmarVinculoPrevia(fichaId, indice) {
  const alvo = _conciliacaoOutros[indice];
  const linha = parseInt(document.getElementById(`previa-sel-${indice}`)?.value, 10);
  if (!alvo || !linha) { toast('Escolha a compra', 'error'); return; }

  try {
    await api(`/pedidos/${linha}`, {
      method: 'PUT',
      body: JSON.stringify({
        cliente: alvo.cliente,
        peca: alvo.modelo || '',
        numero_os: alvo.numero_os || '',
      }),
    });
    toast(`Peça vinculada a ${alvo.cliente}`, 'success');
    carregarSeloPecas();
    abrirConciliacao(fichaId);   // refaz a prévia, agora com o vínculo valendo
  } catch (e) { toast(e.message, 'error'); }
}

async function aplicarConciliacao(fichaId) {
  const btn = document.getElementById('btn-aplicar-conciliacao');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Gravando...';
  try {
    const r = await api(`/fichas/${fichaId}/conciliar?aplicar=true`, { method: 'POST' });
    fecharModais();
    toast(`Planilha atualizada: ${(r.casados || []).length} baixa(s), ${(r.outros || []).length} em Outros`, 'success');
  } catch (e) {
    toast(e.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Tentar de novo';
  }
}

// ─── Folha de desfecho (painel) ─────────────────────────────────────
//
// Mesmas quatro opções do app do técnico, e grava pela mesma função no
// servidor: o desfecho não pode depender de quem concluiu, senão o relatório
// vira duas contagens diferentes.
const DF_OPCOES = [
  { tipo: 'resolvido',    rotulo: 'Resolvido',       sub: 'consertado na hora' },
  { tipo: 'precisa_peca', rotulo: 'Precisa de peça', sub: 'diagnosticado, falta peça' },
  { tipo: 'cotacao_peca', rotulo: 'Cotação de peça', sub: 'não sei o preço ainda' },
  { tipo: 'volto_depois', rotulo: 'Volta depois',    sub: 'precisa retornar' },
  { tipo: 'nao_atendido', rotulo: 'Reagendar',       sub: 'não deu para fazer, precisa remarcar' },
];
const DF_MOTIVOS = ['Cliente ausente', 'Endereço errado', 'Cliente recusou',
                    'Aparelho sem defeito', 'Sem acesso ao local'];

let _dfServico = null, _dfFicha = null, _dfTipo = null, _dfFoto = null;

// Reduz mantendo a imagem INTEIRA — sem recorte.
//
// O reduzirImagem() daqui corta um quadrado central, porque foi escrito para
// foto de perfil de técnico. Numa etiqueta isso decepa justamente o número de
// série, que é o dado pelo qual a peça é pedida. 1280px no lado maior é o que
// mantém legível um código impresso pequeno.
async function reduzirFotoInteira(arquivo, ladoMaximo = 1280, qualidade = 0.72) {
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

  // Duas tentativas por causa do HEIC do iPhone, que a maioria dos
  // navegadores não decodifica pela tag <img> — a imagem não carrega e o
  // erro morre calado.
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
          ? 'Foto em HEIC (formato do iPhone) — o navegador não abre. Envie um print, ou mude em Ajustes > Câmera > Formatos > "Mais compatível".'
          : 'Não consegui abrir essa foto.'));
    };
    img.src = url;
  });
}

function blocoFotoPainel() {
  return `
    <label class="form-label" style="margin-top:14px;">Foto da etiqueta</label>
    <p class="df-ajuda">É dela que sai o modelo e o número de série para pedir a peça.</p>
    <label class="df-foto-botao">
      Escolher foto
      <input type="file" accept="image/*" onchange="escolherFotoDesfecho(this)" hidden>
    </label>
    <div id="df-previa" class="df-previa"></div>`;
}

async function escolherFotoDesfecho(input) {
  const arquivo = input.files && input.files[0];
  if (!arquivo) return;
  const previa = document.getElementById('df-previa');
  previa.innerHTML = '<span class="df-processando">preparando a foto...</span>';
  try {
    _dfFoto = await reduzirFotoInteira(arquivo);
    previa.innerHTML = `
      <img class="df-thumb" src="${_dfFoto}" alt="Etiqueta do aparelho">
      <button type="button" class="df-remover-foto" onclick="removerFotoDesfecho()">remover</button>`;
  } catch (e) {
    _dfFoto = null;
    previa.innerHTML = `<span class="df-erro">${esc(e.message)}</span>`;
  } finally {
    input.value = '';   // permite reescolher a MESMA foto depois de remover
    validarConfirmarDesfecho();
  }
}

function removerFotoDesfecho() {
  _dfFoto = null;
  const previa = document.getElementById('df-previa');
  if (previa) previa.innerHTML = '';
  validarConfirmarDesfecho();
}

function abrirDesfecho(servicoId, fichaId) {
  _dfServico = servicoId; _dfFicha = fichaId; _dfTipo = null; _dfFoto = null;
  const m = document.getElementById('modal-desfecho');
  m.querySelector('.df-corpo').innerHTML = `
    <div class="df-opcoes">
      ${DF_OPCOES.map(o => `
        <button class="df-opcao" data-tipo="${o.tipo}" onclick="escolherDesfecho('${o.tipo}')">
          <b>${o.rotulo}</b><small>${o.sub}</small>
        </button>`).join('')}
    </div>
    <div id="df-extra"></div>`;
  document.getElementById('df-confirmar').disabled = true;
  m.classList.add('open');
}

function fecharDesfecho() {
  document.getElementById('modal-desfecho')?.classList.remove('open');
  _dfServico = null;
}

function escolherDesfecho(tipo) {
  _dfTipo = tipo;
  document.querySelectorAll('.df-opcao').forEach(b =>
    b.classList.toggle('ativa', b.dataset.tipo === tipo));
  const extra = document.getElementById('df-extra');
  if (tipo === 'precisa_peca') {
    extra.innerHTML = `<label class="form-label" for="df-peca">Qual peça?</label>
      <input class="form-input" id="df-peca" autocomplete="off"
             placeholder="Código ou nome da peça">
      ${blocoFotoPainel()}`;
    setTimeout(() => document.getElementById('df-peca')?.focus(), 60);
  } else if (tipo === 'cotacao_peca') {
    // Código, nome e foto obrigatórios — mesma regra do app do técnico
    // (ver validarConfirmarDesfecho). Sem os três não dá pra cotar direito.
    extra.innerHTML = `<label class="form-label" for="df-codigo">Código da peça</label>
      <input class="form-input" id="df-codigo" autocomplete="off"
             placeholder="Ex: DE97-01234A" oninput="validarConfirmarDesfecho()">
      <label class="form-label" style="margin-top:10px;" for="df-nome-peca">Nome da peça</label>
      <input class="form-input" id="df-nome-peca" autocomplete="off"
             placeholder="Ex: Placa eletrônica" oninput="validarConfirmarDesfecho()">
      ${blocoFotoPainel()}`;
    setTimeout(() => document.getElementById('df-codigo')?.focus(), 60);
  } else if (tipo === 'nao_atendido') {
    extra.innerHTML = `<label class="form-label">Por quê?</label>
      <div class="df-motivos">${DF_MOTIVOS.map(mo =>
        `<button class="df-motivo" data-motivo="${esc(mo)}"
                 onclick="escolherMotivoDesfecho(this)">${esc(mo)}</button>`).join('')}</div>`;
  } else {
    extra.innerHTML = '';
  }
  // Observação vale para QUALQUER desfecho: mesmo um "resolvido" pode ter
  // um detalhe que só quem esteve lá sabe. Fica por último e é opcional —
  // as opções acima é que carregam o dado que dá para somar.
  extra.insertAdjacentHTML('beforeend', `
    <label class="form-label" style="margin-top:14px;" for="df-obs">Observação</label>
    <textarea class="form-input df-obs" id="df-obs" rows="3"
              placeholder="Algo que a equipe precisa saber (opcional)"></textarea>`);
  validarConfirmarDesfecho();
}

// Só cotação de peça trava o botão — os demais desfechos continuam podendo
// ser confirmados só com o tipo escolhido, igual sempre foi.
function validarConfirmarDesfecho() {
  const btn = document.getElementById('df-confirmar');
  if (!btn) return;
  let ok = true;
  if (_dfTipo === 'cotacao_peca') {
    const codigo = document.getElementById('df-codigo')?.value.trim();
    const nome = document.getElementById('df-nome-peca')?.value.trim();
    ok = !!(codigo && nome && _dfFoto);
  }
  btn.disabled = !ok;
}

function escolherMotivoDesfecho(botao) {
  document.querySelectorAll('.df-motivo').forEach(b => b.classList.remove('ativa'));
  botao.classList.add('ativa');
}

async function confirmarDesfecho() {
  if (!_dfTipo || !_dfServico) return;
  const desfecho = { tipo: _dfTipo };
  if (_dfTipo === 'precisa_peca') desfecho.peca = document.getElementById('df-peca')?.value.trim() || '';
  if (_dfTipo === 'cotacao_peca') {
    desfecho.codigo = document.getElementById('df-codigo')?.value.trim() || '';
    desfecho.nome_peca = document.getElementById('df-nome-peca')?.value.trim() || '';
  }
  if (_dfTipo === 'nao_atendido') desfecho.motivo = document.querySelector('.df-motivo.ativa')?.dataset.motivo || '';
  const obs = document.getElementById('df-obs')?.value.trim();
  if (obs) desfecho.observacao = obs;
  if (_dfFoto) desfecho.foto = _dfFoto;
  const svc = _dfServico, ficha = _dfFicha;
  fecharDesfecho();
  await alternarStatusServico(svc, 'concluido', ficha, desfecho);
}

async function alternarStatusServico(servicoId, novoStatus, fichaId, desfecho) {
  try {
    await api(`/servicos/${servicoId}/status`, {
      method: 'PUT',
      body: JSON.stringify(desfecho ? { status: novoStatus, desfecho } : { status: novoStatus }),
    });
    toast(novoStatus === 'concluido' ? 'Atendimento marcado como feito' : 'Atendimento reaberto', 'success');
    await renderFichaDetalhe(fichaId);
  } catch (e) { toast(e.message, 'error'); }
}

function abrirModalNovoTecnico() {
  document.getElementById('novo-tecnico-nome').value = '';
  document.getElementById('modal-novo-tecnico').classList.add('open');
  setTimeout(() => document.getElementById('novo-tecnico-nome').focus(), 100);
}

function abrirModalNovaFicha(tecnicoId) {
  document.getElementById('nova-ficha-tecnico-id').value = tecnicoId;
  document.getElementById('nova-dia').value = '';
  document.querySelectorAll('.dia-pill').forEach(p => p.classList.remove('selected'));
  document.getElementById('nova-data').value = '';
  document.getElementById('nova-partida-cep').value = '';
  document.getElementById('nova-partida-nome').value = '';
  document.getElementById('modal-nova-ficha').classList.add('open');
}

function abrirModalAddServico(fichaId) {
  document.getElementById('add-ficha-id').value = fichaId;
  ['add-cep','add-numero','add-cliente','add-telefone','add-descricao','add-tipo-aparelho','add-modelo','add-numero-os']
    .forEach(id => { document.getElementById(id).value = ''; });
  preencherSelectSetor('add-setor');
  document.getElementById('modal-add-servico').classList.add('open');
  setTimeout(() => document.getElementById('add-cep').focus(), 100);
}

function abrirModalEditarServico(servicoId) {
  const s = servicosAtuais.find(x => x.id === servicoId);
  if (!s) { toast('Atendimento não encontrado — recarregue a ficha', 'error'); return; }

  document.getElementById('edit-servico-id').value = servicoId;
  document.getElementById('edit-ficha-id').value = fichaAtiva?.id || '';
  document.getElementById('edit-cep').value = formatCEP(s.cep);
  document.getElementById('edit-numero').value = s.numero || '';
  document.getElementById('edit-cliente').value = s.cliente || '';
  document.getElementById('edit-telefone').value = s.telefone || '';
  document.getElementById('edit-tipo-aparelho').value = s.tipo_aparelho || '';
  document.getElementById('edit-modelo').value = s.modelo || '';
  document.getElementById('edit-numero-os').value = s.numero_os || '';
  preencherSelectSetor('edit-setor', s.setor_id);
  document.getElementById('edit-descricao').value = s.descricao || '';

  montarReagendar();

  document.getElementById('modal-editar-servico').classList.add('open');
  setTimeout(() => document.getElementById('edit-cliente').focus(), 100);
}

// ─── Reagendar: técnico + dia num lugar só ──────────────────────────
// Junta o que antes eram duas coisas separadas (mudar de dia num campo,
// transferir de técnico noutro botão). O Kalebe quer trocar o técnico E o dia
// da mesma tela. Escolher um técnico recarrega os dias DELE.
let _reagTecnico = null;   // técnico escolhido (null = mantém o atual)
let _reagFicha = null;     // ficha de destino escolhida (null = mantém)

function montarReagendar() {
  _reagTecnico = fichaAtiva?.tecnico_id || null;
  _reagFicha = null;

  const alvo = document.getElementById('edit-reag-tecnicos');
  alvo.innerHTML = (tecnicos || []).map(t => `
    <button type="button" class="reag-tec ${t.id === _reagTecnico ? 'sel' : ''}"
            data-tec="${t.id}" onclick="escolherReagTecnico(${t.id})"
            style="--cor:${escCor(t.cor)}">
      <span class="reag-bolinha" style="background:${escCor(t.cor)}"></span>${esc(t.nome)}
    </button>`).join('');

  montarReagDias();
}

function escolherReagTecnico(id) {
  _reagTecnico = id;
  _reagFicha = null;   // trocou de técnico: os dias são outros
  document.querySelectorAll('#edit-reag-tecnicos .reag-tec').forEach(b =>
    b.classList.toggle('sel', Number(b.dataset.tec) === id));
  montarReagDias();
}

async function montarReagDias() {
  const alvo = document.getElementById('edit-reag-dias');
  alvo.innerHTML = '<span class="reag-vazio">Carregando dias...</span>';

  let fichas;
  try {
    fichas = await api(`/fichas?tecnico_id=${_reagTecnico}&abertas=true`);
  } catch { alvo.innerHTML = '<span class="reag-vazio">Não consegui carregar os dias.</span>'; return; }

  const mesmoTecnico = _reagTecnico === fichaAtiva?.tecnico_id;
  const hoje = dataDeHoje();

  // Do mesmo técnico, a ficha onde o ponto já está aparece como "atual" e fica
  // marcada; das outras fichas ou de outro técnico, todas são destinos.
  const cards = (fichas || []).map(f => {
    const atual = mesmoTecnico && f.id === fichaAtiva?.id;
    const data = f.data_referencia ? formatarData(f.data_referencia) : 'sem data';
    const hojeTag = f.data_referencia === hoje ? '<span class="reag-hoje">hoje</span>' : '';
    return `
      <button type="button" class="reag-dia ${atual ? 'atual' : ''}"
              data-ficha="${f.id}" ${atual ? 'disabled' : `onclick="escolherReagDia(${f.id})"`}>
        <span class="reag-dia-nome">${esc(f.dia_semana)} ${hojeTag}</span>
        <span class="reag-dia-meta">${esc(data)} · ${f.total_servicos} atend.${atual ? ' · atual' : ''}</span>
      </button>`;
  }).join('');

  const semDias = !(fichas || []).some(f => !(mesmoTecnico && f.id === fichaAtiva?.id));

  // Botão de criar dia direto aqui — antes mandava "criar na barra lateral",
  // o que obrigava a fechar o modal, criar, e voltar. Agora cria e já usa.
  const criador = `
    <div class="reag-novo">
      <button type="button" class="reag-novo-btn" onclick="toggleNovoDiaReag()">+ Criar dia novo</button>
      <div class="reag-novo-form" id="reag-novo-form" style="display:none;">
        <input type="date" class="form-input" id="reag-novo-data" min="${hoje}">
        <button type="button" class="btn btn-primary btn-sm" onclick="criarDiaReag()">Criar e usar</button>
      </div>
    </div>`;

  const aviso = semDias
    ? '<span class="reag-vazio">Esse técnico não tem outro dia em aberto — crie um abaixo.</span>'
    : '';
  alvo.innerHTML = cards + aviso + criador;
}

function toggleNovoDiaReag() {
  const f = document.getElementById('reag-novo-form');
  if (!f) return;
  const abrir = f.style.display === 'none';
  f.style.display = abrir ? 'flex' : 'none';
  if (abrir) setTimeout(() => document.getElementById('reag-novo-data')?.focus(), 40);
}

// Nome do dia da semana (pt-BR, capitalizado) a partir de "AAAA-MM-DD".
// Constrói a data em fuso LOCAL — new Date('AAAA-MM-DD') seria UTC e podia
// voltar o dia da semana errado perto da virada do dia.
function diaSemanaDeData(dataStr) {
  const [y, m, d] = (dataStr || '').split('-').map(Number);
  if (!y || !m || !d) return '';
  const nome = new Date(y, m - 1, d).toLocaleDateString('pt-BR', { weekday: 'long' });
  return nome.charAt(0).toUpperCase() + nome.slice(1);
}

// Cria a ficha (dia) para o técnico escolhido no reagendar e já a seleciona
// como destino — o Salvar então move o atendimento para lá.
async function criarDiaReag() {
  const data = document.getElementById('reag-novo-data')?.value;
  if (!data) { toast('Escolha a data do novo dia.', 'error'); return; }
  const dia = diaSemanaDeData(data);
  if (!dia) { toast('Data inválida.', 'error'); return; }
  if (!_reagTecnico) { toast('Escolha o técnico primeiro.', 'error'); return; }

  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify({
      tecnico_id: _reagTecnico, dia_semana: dia, data_referencia: data,
    }) });
    toast(`Dia ${dia} (${formatarData(data)}) criado`, 'success');
    await montarReagDias();          // redesenha a lista com o dia novo
    escolherReagDia(r.id);           // já deixa selecionado como destino
  } catch (e) { toast(e.message, 'error'); }
}

function escolherReagDia(fichaId) {
  _reagFicha = fichaId;
  document.querySelectorAll('#edit-reag-dias .reag-dia').forEach(b =>
    b.classList.toggle('sel', Number(b.dataset.ficha) === fichaId));
}

async function salvarEdicaoServico() {
  const servicoId = document.getElementById('edit-servico-id').value;
  const fichaId = document.getElementById('edit-ficha-id').value;
  const cep = document.getElementById('edit-cep').value.replace(/\D/g, '');

  if (cep.length !== 8) { toast('Informe um CEP válido', 'error'); return; }

  // As duas checagens vêm ANTES de travar o botão — um retorno antecipado
  // depois do `btn.disabled = true` deixava "Salvando..." preso pra sempre,
  // já que o `finally` só cobre o `try` que vem depois (mesmo defeito que
  // adicionarServico() teve e foi corrigido em 2026-08-13).
  const setorEditado = document.getElementById('edit-setor').value;
  if (!setorEditado) {
    toast('Escolha o setor do atendimento.', 'error');
    document.getElementById('edit-setor').focus();
    return;
  }

  const telefoneEditado = document.getElementById('edit-telefone').value.trim();
  if (!telefoneEditado) {
    toast('Informe o telefone do cliente.', 'error');
    document.getElementById('edit-telefone').focus();
    return;
  }

  const btn = document.getElementById('btn-editar-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Salvando...';

  try {
    await api(`/servicos/${servicoId}`, {
      method: 'PUT',
      body: JSON.stringify({
        cep,
        numero:        document.getElementById('edit-numero').value,
        cliente:       document.getElementById('edit-cliente').value,
        telefone:      telefoneEditado,
        descricao:     document.getElementById('edit-descricao').value,
        tipo_aparelho: document.getElementById('edit-tipo-aparelho').value,
        modelo:        document.getElementById('edit-modelo').value,
        numero_os:     document.getElementById('edit-numero-os').value,
        setor_id:      setorEditado,
      }),
    });

    lembrarSetor(setorEditado);

    // Reagendamento, DEPOIS de gravar os dados — assim o que foi editado vai
    // junto. Duas situações, decididas pelo que a pessoa escolheu:
    //  - outro técnico  -> transferir (encerra rastreio, cria ficha se preciso)
    //  - mesmo técnico, outro dia -> mover entre fichas
    let remanejou = false;
    const trocouTecnico = _reagTecnico && _reagTecnico !== fichaAtiva?.tecnico_id;

    if (trocouTecnico) {
      const r = await api(`/servicos/${servicoId}/tecnico`, {
        method: 'PUT', body: JSON.stringify({ tecnico_id: _reagTecnico }),
      });
      remanejou = true;
      toast(r.mensagem || 'Atendimento transferido', 'success');
    } else if (_reagFicha && _reagFicha !== fichaAtiva?.id) {
      const r = await api(`/servicos/${servicoId}/mover`, {
        method: 'PUT', body: JSON.stringify({ ficha_id: _reagFicha }),
      });
      remanejou = true;
      toast(r.mensagem || 'Atendimento movido de dia', 'success');
    }

    fecharModais();
    let movido = remanejou;
    if (!movido) toast('Atendimento atualizado', 'success');
    // Se moveu, a ficha atual perdeu o ponto — recarregar a de origem mostra
    // o dia sem ele, que é o resultado esperado.
    await renderFichaDetalhe(parseInt(fichaId, 10));
    await carregarTecnicos();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Salvar Alterações';
  }
}

// ═══ Ordens de Serviço ═══════════════════════════════════════════════════
// A OS é o documento (cliente, equipamento, defeito, status). QUEM atende e
// QUANDO continuam sendo o sistema de fichas/técnicos — a OS só se liga a um
// servico (ver rotas/ordens_servico.py) em vez de duplicar agenda.
const OS_STATUS_ROTULO = {
  aguardando_agendamento: 'Aguardando agendamento',
  agendada:               'Agendada',
  em_atendimento:         'Em atendimento',
  aguardando_peca:        'Aguardando peça',
  aguardando_orcamento:   'Aguardando orçamento',
  aguardando_aprovacao:   'Aguardando aprovação',
  aprovada:               'Aprovada',
  finalizada:             'Finalizada',
  cancelada:              'Cancelada',
};

let _osFiltroStatus = '';
let _osFiltroDias = '';
let _osBuscaTexto = '';
let _osBuscaTimer = null;
let _osClienteSelecionado = null;   // {id, nome} — null enquanto não escolhido
let _osBuscaClienteTimer = null;
let _osIndicacoesCarregadas = false;

function osBuscar(valor) {
  clearTimeout(_osBuscaTimer);
  _osBuscaTimer = setTimeout(() => {
    _osBuscaTexto = valor.trim();
    carregarOS();
  }, 300);
}

async function carregarOS() {
  const mount = document.getElementById('os-conteudo');
  if (!mount) return;
  mount.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:30px;"><div class="spinner"></div> Carregando...</div>`;

  const params = new URLSearchParams();
  if (_osFiltroStatus) params.set('status', _osFiltroStatus);
  if (_osBuscaTexto) params.set('busca', _osBuscaTexto);
  if (_osFiltroDias) params.set('dias', _osFiltroDias);

  let r;
  try {
    r = await api(`/ordens-servico${params.toString() ? '?' + params.toString() : ''}`);
  } catch (e) {
    mount.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const cartoes = Object.entries(OS_STATUS_ROTULO).map(([chave, rotulo]) => `
    <button class="os-cartao${_osFiltroStatus === chave ? ' ativo' : ''}" onclick="osFiltrar('${chave}')">
      <div class="n">${r.contagem[chave] ?? 0}</div>
      <div class="rot">${rotulo}</div>
    </button>`).join('');

  if (r.ordens.length === 0) {
    mount.innerHTML = `<div class="os-cartoes">${cartoes}</div>
      <div class="historico-vazio">${icone('check', 'icone-24')}
        <p>${_osFiltroStatus ? 'Nenhuma OS nesse status.' : 'Nenhuma ordem de serviço aberta ainda.'}</p></div>`;
    return;
  }

  const linhas = r.ordens.map(o => `
    <div class="os-linha" onclick="abrirOSDetalhe(${o.id})">
      <div class="num">OS #${String(o.id).padStart(6, '0')}</div>
      <div>
        <div class="cliente">${esc(o.cliente_nome)}</div>
        <div class="aparelho">${esc([o.tipo_aparelho, o.marca, o.modelo].filter(Boolean).join(' · ')) || '—'}</div>
      </div>
      <div class="defeito">${esc(o.defeito_declarado || '—')}</div>
      <span class="conc-tag ${o.status === 'finalizada' ? 'ok' : o.status === 'cancelada' ? 'neutro' : 'aviso'}">${esc(OS_STATUS_ROTULO[o.status] || o.status)}</span>
    </div>`).join('');

  mount.innerHTML = `<div class="os-cartoes">${cartoes}</div>${linhas}`;
}

// ─── Agendar Clientes: fila de quem está pronto pra ter visita marcada ──
//
// É a mesma OS que a aba OS já lista, só que fixada no status
// 'aguardando_agendamento' — toda OS nova nasce nesse status, e uma peça
// que chegou (aba Peças) também cai aqui via /pedidos/<linha>/agendar-cliente.
// Uma fila só, em vez de duas listas que ninguém sabe qual conferir.
async function carregarAgendarClientes() {
  const mount = document.getElementById('agendar-conteudo');
  if (!mount) return;
  mount.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:30px;"><div class="spinner"></div> Carregando...</div>`;

  let r;
  try {
    r = await api('/ordens-servico?status=aguardando_agendamento');
  } catch (e) {
    mount.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  atualizarSeloAgendar(r.ordens.length);

  if (r.ordens.length === 0) {
    mount.innerHTML = `<div class="historico-vazio">${icone('check', 'icone-24')}
      <p>Ninguém esperando agendamento no momento.</p></div>`;
    return;
  }

  mount.innerHTML = r.ordens.map(o => `
    <div class="agendar-card" onclick="abrirOSDetalhe(${o.id})">
      <div class="agendar-card-topo">
        <div class="agendar-cliente">${esc(o.cliente_nome)}</div>
        <span class="agendar-espera">${esperandoHa(o.criado_em)}</span>
      </div>
      <div class="agendar-linha-info">
        ${icone('telefone', 'icone-13')}
        ${o.cliente_telefone
          ? `<a href="tel:${esc(o.cliente_telefone.replace(/\D/g, ''))}" onclick="event.stopPropagation()">${esc(o.cliente_telefone)}</a>`
          : `<span class="agendar-sem-info">sem telefone cadastrado</span>`}
        <span class="agendar-sep">·</span>
        <span>OS #${String(o.id).padStart(6, '0')}</span>
      </div>
      <div class="agendar-linha-info">
        <span class="agendar-aparelho">${esc([o.tipo_aparelho, o.marca, o.modelo].filter(Boolean).join(' · ')) || 'aparelho não informado'}</span>
      </div>
      ${o.defeito_declarado ? `<div class="agendar-defeito">${esc(o.defeito_declarado)}</div>` : ''}
      <button type="button" class="btn btn-primary btn-sm agendar-btn"
              onclick="event.stopPropagation(); abrirOSDetalhe(${o.id})">
        Agendar visita →
      </button>
    </div>`).join('');
}

// "há 3 dias" / "hoje" / "há 2h" — pra fila mostrar quem está esperando há
// mais tempo sem ter que abrir cada card pra ler a data por extenso.
function esperandoHa(criadoEmTxt) {
  const d = parseDataBanco(criadoEmTxt);
  if (!d) return '';
  const min = Math.round((new Date() - d) / 60000);
  if (min < 60) return 'há pouco';
  const horas = Math.round(min / 60);
  if (horas < 24) return `há ${horas}h`;
  const dias = Math.round(horas / 24);
  return dias === 1 ? 'há 1 dia' : `há ${dias} dias`;
}

// Selo com quantos clientes esperam agendamento — sem isso a fila só é vista
// por quem lembra de clicar na aba, e é exatamente o que não pode acontecer
// com peça já na mão do cliente esperando.
function atualizarSeloAgendar(qtd) {
  const aba = document.getElementById('mtab-agendar');
  if (!aba) return;
  aba.querySelector('.aba-selo')?.remove();
  if (qtd > 0) {
    const selo = document.createElement('span');
    selo.className = 'aba-selo';
    selo.textContent = qtd;
    selo.title = `${qtd} cliente(s) esperando agendamento`;
    aba.appendChild(selo);
  }
}

async function carregarSeloAgendar() {
  // Se a aba já está aberta na tela, redesenha a lista de verdade (não só o
  // selo) — sem isso, agendar um cliente pela aba OS deixava o card dele
  // fantasma na fila de Agendar Clientes até alguém trocar de aba e voltar.
  if (document.getElementById('panel-agendar')?.style.display !== 'none') {
    carregarAgendarClientes();
    return;
  }
  try {
    const r = await api('/ordens-servico?status=aguardando_agendamento');
    atualizarSeloAgendar(r.ordens.length);
  } catch (e) { /* sem selo, sem barulho — a aba já mostra ao abrir */ }
}

async function carregarOSMetricas() {
  const mount = document.getElementById('os-metricas-conteudo');
  if (!mount) return;
  mount.innerHTML = `<p class="ajuda-texto">carregando...</p>`;

  let r;
  try {
    r = await api('/ordens-servico/metricas');
  } catch (e) {
    mount.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const mesNome = (m) => {
    const [ano, mes] = m.split('-');
    const nomes = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
    return `${nomes[Number(mes) - 1]}/${ano.slice(2)}`;
  };

  const cartoes = `
    <div class="os-cartoes" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));">
      <div class="os-cartao" style="cursor:default;">
        <div class="n">${r.total_geral}</div>
        <div class="rot">OS no total</div>
      </div>
      <div class="os-cartao" style="cursor:default;">
        <div class="n">${r.tempo_medio_dias ?? '—'}${r.tempo_medio_dias !== null ? 'd' : ''}</div>
        <div class="rot">Tempo médio até finalizar${r.os_finalizadas_com_tempo ? ' (' + r.os_finalizadas_com_tempo + ' OS)' : ''}</div>
      </div>
    </div>`;

  const porMes = r.por_mes.length === 0 ? `<p class="ajuda-texto">Sem dados ainda.</p>` : `
    <div style="display:flex;gap:8px;align-items:flex-end;height:70px;margin-top:6px;">
      ${(() => {
        const maior = Math.max(...r.por_mes.map(m => m.total), 1);
        return r.por_mes.map(m => `
          <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">
            <span style="font-size:11px;color:var(--text-muted);">${m.total}</span>
            <div style="width:100%;background:var(--accent);border-radius:4px 4px 0 0;height:${Math.max(4, (m.total / maior) * 44)}px;"></div>
            <span style="font-size:10px;color:var(--text-muted);">${mesNome(m.mes)}</span>
          </div>`).join('');
      })()}
    </div>`;

  const porIndicacao = r.por_indicacao.length === 0 ? `<p class="ajuda-texto">Sem indicação registrada ainda.</p>` :
    r.por_indicacao.map(i => `
      <div class="os-visita-linha">
        <span>${esc(i.indicacao)}</span>
        <span class="badge accent">${i.total}</span>
      </div>`).join('');

  mount.innerHTML = `
    ${cartoes}
    <p class="form-separador">OS abertas por mês</p>
    ${porMes}
    <p class="form-separador">De onde vêm os clientes</p>
    ${porIndicacao}`;
}

// Chamado depois de QUALQUER entrada no estoque (manual, nota, bipar). A
// peça que acabou de chegar pode ser exatamente a que uma OS em "aguardando
// peça" está esperando — sem isso, ninguém lembra de olhar a lista de OS
// depois de guardar a caixa na prateleira.
function osAvisarEsperando(lista) {
  (lista || []).forEach(o => {
    const aparelho = [o.tipo_aparelho, o.modelo].filter(Boolean).join(' ');
    toast(`Peça chegou — OS #${String(o.id).padStart(6, '0')} (${esc(o.cliente_nome)}${aparelho ? ', ' + esc(aparelho) : ''}) estava esperando`, 'info');
  });
}

function osExportar() {
  const params = new URLSearchParams();
  if (_osFiltroStatus) params.set('status', _osFiltroStatus);
  if (_osBuscaTexto) params.set('busca', _osBuscaTexto);
  if (_osFiltroDias) params.set('dias', _osFiltroDias);
  // Exportação é download direto, não JSON — mesmos filtros da tela, mas
  // fora do api() (que espera resposta JSON).
  window.open(`${BASE}/api/ordens-servico/exportar${params.toString() ? '?' + params.toString() : ''}`, '_blank');
}

function osMudarPeriodo(dias) {
  _osFiltroDias = dias;
  document.querySelectorAll('#os-periodo .at-per').forEach(b =>
    b.classList.toggle('ativo', b.dataset.dias === String(dias)));
  carregarOS();
}

function osFiltrar(status) {
  _osFiltroStatus = (_osFiltroStatus === status) ? '' : status;
  carregarOS();
}

async function abrirModalNovaOS() {
  _osClienteSelecionado = null;
  ['os-nome','os-cpf','os-telefone','os-email','os-cep','os-numero','os-bairro',
   'os-cidade','os-endereco','os-estado','os-tipo-aparelho','os-marca','os-modelo',
   'os-serie','os-acessorios','os-defeito','os-obs'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('os-taxa').value = '0';
  document.getElementById('os-cep-status').textContent = '';
  _osCepUltimo = '';
  document.getElementById('os-busca-cliente').value = '';
  document.getElementById('os-resultado-cliente').innerHTML = '';
  document.getElementById('os-historico-cliente').innerHTML = '';
  osEscolherModoCliente('existente');

  if (!_osIndicacoesCarregadas) {
    try {
      const r = await api('/clientes/indicacoes');
      const sel = document.getElementById('os-indicacao');
      sel.innerHTML = '<option value="">Selecione...</option>' +
        r.indicacoes.map(i => `<option value="${esc(i)}">${esc(i)}</option>`).join('');
      _osIndicacoesCarregadas = true;
    } catch { /* select fica só com "Selecione..." se falhar */ }
  }

  document.getElementById('modal-nova-os').classList.add('open');
}

let _osCepUltimo = '';

async function osBuscarCep(valor) {
  const cep = (valor || '').replace(/\D/g, '');
  const status = document.getElementById('os-cep-status');
  if (cep.length !== 8) {
    status.textContent = '';
    return;
  }
  if (cep === _osCepUltimo) return;  // já buscou esse CEP, não repete a toa
  _osCepUltimo = cep;

  status.textContent = 'buscando endereço...';
  try {
    const r = await api(`/clientes/cep/${cep}`);
    document.getElementById('os-endereco').value = r.endereco || '';
    document.getElementById('os-bairro').value = r.bairro || '';
    document.getElementById('os-cidade').value = r.cidade || '';
    document.getElementById('os-estado').value = r.estado || '';
    status.textContent = r.endereco ? '' : 'CEP achado, mas sem rua (preencha na mão)';
    // Foco vai pro número: é o único dado que o CEP nunca traz, e a pessoa
    // já está com a mão no teclado — economiza um clique.
    document.getElementById('os-numero').focus();
  } catch {
    status.textContent = 'CEP não encontrado — preencha o endereço na mão';
  }
}

function osEscolherModoCliente(modo) {
  document.querySelectorAll('#os-cliente-modo .pecas-filtro').forEach(b =>
    b.classList.toggle('ativo', b.dataset.modo === modo));
  document.getElementById('os-cliente-existente').style.display = modo === 'existente' ? '' : 'none';
  document.getElementById('os-cliente-novo').style.display = modo === 'novo' ? '' : 'none';
}

function osBuscarCliente(termo) {
  clearTimeout(_osBuscaClienteTimer);
  const alvo = document.getElementById('os-resultado-cliente');
  if (!termo || termo.trim().length < 2) {
    alvo.innerHTML = '';
    return;
  }
  _osBuscaClienteTimer = setTimeout(async () => {
    let r;
    try {
      r = await api(`/clientes?busca=${encodeURIComponent(termo.trim())}`);
    } catch (e) {
      alvo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
      return;
    }
    if (r.clientes.length === 0) {
      alvo.innerHTML = `<p class="ajuda-texto" style="margin-top:8px;">Ninguém encontrado — use "Cliente novo".</p>`;
      return;
    }
    alvo.innerHTML = r.clientes.map(c => `
      <div class="os-resultado-item${_osClienteSelecionado?.id === c.id ? ' selecionado' : ''}"
           onclick='osSelecionarCliente(${c.id}, ${JSON.stringify(c.nome)})'>
        <b>${esc(c.nome)}</b>
        <span>${esc(c.telefone || '')}${c.cpf_cnpj ? ' · ' + esc(c.cpf_cnpj) : ''}</span>
      </div>`).join('');
  }, 350);
}

async function osSelecionarCliente(id, nome) {
  _osClienteSelecionado = { id, nome };
  document.querySelectorAll('.os-resultado-item').forEach(el => el.classList.remove('selecionado'));
  osBuscarCliente(document.getElementById('os-busca-cliente').value);

  // Cliente que já veio antes é sinal — "trouxe a mesma geladeira 3 vezes"
  // é informação que muda a conversa com quem está atendendo agora.
  const alvo = document.getElementById('os-historico-cliente');
  alvo.innerHTML = `<p class="ajuda-texto">carregando histórico...</p>`;
  try {
    const r = await api(`/clientes/${id}`);
    const anteriores = r.ordens_servico || [];
    if (anteriores.length === 0) {
      alvo.innerHTML = `<p class="ajuda-texto">Primeira OS deste cliente.</p>`;
      return;
    }
    alvo.innerHTML = `
      <p class="ajuda-texto" style="margin-bottom:6px;">
        ${anteriores.length} OS anterior${anteriores.length !== 1 ? 'es' : ''} deste cliente:
      </p>
      ${anteriores.map(o => `
        <div class="os-visita-linha">
          <span>OS #${String(o.id).padStart(6, '0')} · ${esc([o.tipo_aparelho, o.modelo].filter(Boolean).join(' ')) || 'sem aparelho'} — ${esc(o.defeito_declarado || '')}</span>
          <span class="conc-tag ${o.status === 'finalizada' ? 'ok' : o.status === 'cancelada' ? 'neutro' : 'aviso'}">${esc(OS_STATUS_ROTULO[o.status] || o.status)}</span>
        </div>`).join('')}`;
  } catch {
    alvo.innerHTML = '';
  }
}

async function osCriar() {
  const modo = document.querySelector('#os-cliente-modo .pecas-filtro.ativo')?.dataset.modo;
  const corpo = {
    tipo_aparelho: document.getElementById('os-tipo-aparelho').value.trim(),
    marca: document.getElementById('os-marca').value.trim(),
    modelo: document.getElementById('os-modelo').value.trim(),
    numero_serie: document.getElementById('os-serie').value.trim(),
    acessorios: document.getElementById('os-acessorios').value.trim(),
    defeito_declarado: document.getElementById('os-defeito').value.trim(),
    taxa_avaliacao: document.getElementById('os-taxa').value || 0,
    observacao: document.getElementById('os-obs').value.trim(),
  };

  if (modo === 'existente') {
    if (!_osClienteSelecionado) {
      toast('Escolha um cliente na busca, ou mude pra "Cliente novo"', 'error');
      return;
    }
    corpo.cliente_id = _osClienteSelecionado.id;
  } else {
    const nome = document.getElementById('os-nome').value.trim();
    if (!nome) {
      toast('Informe o nome do cliente', 'error');
      return;
    }
    corpo.cliente_novo = {
      nome, cpf_cnpj: document.getElementById('os-cpf').value.trim(),
      telefone: document.getElementById('os-telefone').value.trim(),
      email: document.getElementById('os-email').value.trim(),
      cep: document.getElementById('os-cep').value.trim(),
      numero: document.getElementById('os-numero').value.trim(),
      bairro: document.getElementById('os-bairro').value.trim(),
      cidade: document.getElementById('os-cidade').value.trim(),
      endereco: document.getElementById('os-endereco').value.trim(),
      estado: document.getElementById('os-estado').value.trim(),
      indicacao: document.getElementById('os-indicacao').value,
    };
  }

  try {
    const resp = await api('/ordens-servico', { method: 'POST', body: JSON.stringify(corpo) });
    toast('OS aberta com sucesso', 'success');
    fecharModais();
    carregarOS();
    carregarSeloAgendar(); // toda OS nova nasce aguardando agendamento
    abrirOSDetalhe(resp.id);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function abrirOSDetalhe(id) {
  let r;
  try {
    r = await api(`/ordens-servico/${id}`);
  } catch (e) {
    toast(e.message, 'error');
    return;
  }
  const o = r.ordem;
  document.getElementById('os-detalhe-titulo').textContent =
    `OS #${String(o.id).padStart(6, '0')} · ${o.cliente_nome}`;

  const visitas = r.visitas.length === 0
    ? `<p class="ajuda-texto">Nenhuma visita agendada ainda.</p>`
    : r.visitas.map(v => `
        <div class="os-visita-linha">
          <span>${esc(v.tecnico_nome || 'sem técnico')} · ${esc(v.data_referencia ? v.data_referencia.split('-').reverse().join('/') : v.dia_semana)}</span>
          <span style="display:flex;align-items:center;gap:8px;">
            <span class="conc-tag ${v.desfecho === 'resolvido' ? 'ok' : v.status === 'concluido' ? 'aviso' : 'neutro'}">${esc(v.desfecho ? (DESFECHO_ROTULO[v.desfecho]?.txt || v.desfecho) : (v.status === 'concluido' ? 'concluído' : 'pendente'))}</span>
            ${v.status === 'pendente' ? `<button class="btn-remove" title="Desagendar — escolheu técnico/dia errado" onclick="osDesagendar(${id}, ${v.id})">${icone('x', 'icone-11')}</button>` : ''}
          </span>
        </div>`).join('');

  const opcoesStatus = Object.entries(OS_STATUS_ROTULO)
    .map(([v, t]) => `<option value="${v}"${o.status === v ? ' selected' : ''}>${t}</option>`).join('');

  const opcoesTecnico = tecnicos.map(t => `<option value="${t.id}">${esc(t.nome)}</option>`).join('');

  document.getElementById('os-detalhe-corpo').innerHTML = `
    <div class="os-detalhe-secao">
      <label class="form-label">Status</label>
      <select class="form-input" onchange="osAtualizarStatus(${o.id}, this.value)">${opcoesStatus}</select>
    </div>
    <div class="os-detalhe-secao">
      <p class="form-separador">Equipamento</p>
      <div class="form-row">
        <div class="form-group"><label class="form-label" for="os-ed-tipo">Tipo</label>
          <input class="form-input" id="os-ed-tipo" value="${esc(o.tipo_aparelho)}"></div>
        <div class="form-group"><label class="form-label" for="os-ed-marca">Marca</label>
          <input class="form-input" id="os-ed-marca" value="${esc(o.marca)}"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label class="form-label" for="os-ed-modelo">Modelo</label>
          <input class="form-input" id="os-ed-modelo" value="${esc(o.modelo)}"></div>
        <div class="form-group"><label class="form-label" for="os-ed-serie">Nº de série</label>
          <input class="form-input" id="os-ed-serie" value="${esc(o.numero_serie)}"></div>
      </div>
      <div class="form-group"><label class="form-label" for="os-ed-acessorios">Acessórios</label>
        <input class="form-input" id="os-ed-acessorios" value="${esc(o.acessorios)}"></div>
      <div class="form-group"><label class="form-label" for="os-ed-defeito">Defeito declarado</label>
        <textarea class="form-input" id="os-ed-defeito" rows="2">${esc(o.defeito_declarado)}</textarea></div>
      <div class="form-row">
        <div class="form-group"><label class="form-label" for="os-ed-taxa">Taxa de avaliação (R$)</label>
          <input class="form-input" type="number" step="0.01" min="0" id="os-ed-taxa" value="${o.taxa_avaliacao ?? 0}"></div>
      </div>
      <div class="form-group"><label class="form-label" for="os-ed-obs">Observação interna</label>
        <textarea class="form-input" id="os-ed-obs" rows="2">${esc(o.observacao)}</textarea></div>
      <button class="btn btn-primary btn-sm" onclick="osSalvarEdicao(${o.id})">Salvar alterações</button>
    </div>
    <div class="os-detalhe-secao">
      <p class="form-separador">Visitas agendadas</p>
      ${visitas}
    </div>
    <div class="os-detalhe-secao">
      <p class="form-separador">Peças usadas</p>
      <div id="os-pecas-lista">${osRenderPecas(r.pecas)}</div>
      <div class="form-row" style="margin-top:8px;">
        <div class="form-group">
          <label class="form-label" for="os-peca-codigo">Código (do estoque)</label>
          <input class="form-input" id="os-peca-codigo" autocomplete="off"
                 onkeydown="if(event.key==='Enter') osAdicionarPeca(${o.id})">
        </div>
        <div class="form-group">
          <label class="form-label" for="os-peca-qtd">Qtd</label>
          <input class="form-input" type="number" min="1" step="1" value="1" id="os-peca-qtd">
        </div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="osAdicionarPeca(${o.id})">+ Adicionar peça</button>
    </div>
    <div class="os-detalhe-secao">
      <p class="form-separador">Agendar nova visita</p>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label" for="os-agendar-tecnico">Técnico</label>
          <select class="form-input" id="os-agendar-tecnico">${opcoesTecnico}</select>
        </div>
        <div class="form-group">
          <label class="form-label" for="os-agendar-data">Data</label>
          <input class="form-input" type="date" id="os-agendar-data" min="${new Date().toISOString().slice(0,10)}">
        </div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="osAgendar(${o.id})">Agendar</button>
    </div>
    <div class="os-detalhe-secao">
      <a class="btn btn-ghost btn-sm" href="/os/${o.id}/imprimir" target="_blank" rel="noopener">${icone('externo', 'icone-13')} Imprimir OS</a>
    </div>`;

  document.getElementById('modal-os-detalhe').classList.add('open');
}

function osRenderPecas(pecas) {
  if (!pecas || pecas.length === 0) {
    return `<p class="ajuda-texto" style="margin:0;">Nenhuma peça baixada ainda.</p>`;
  }
  return pecas.map(p => `
    <div class="os-visita-linha">
      <span><b>${esc(p.codigo)}</b>${p.descricao ? ' — ' + esc(p.descricao) : ''} · ${Number(p.quantidade)}x</span>
      <span style="color:var(--text-muted);font-size:11px;">${esc((p.criado_em || '').split(' ')[0].split('-').reverse().join('/'))}</span>
    </div>`).join('');
}

async function osAdicionarPeca(id) {
  const codigo = document.getElementById('os-peca-codigo').value.trim();
  const qtd = document.getElementById('os-peca-qtd').value || 1;
  if (!codigo) {
    toast('Informe o código da peça', 'error');
    return;
  }
  try {
    await api(`/ordens-servico/${id}/pecas`, {
      method: 'POST', body: JSON.stringify({ codigo, quantidade: qtd }),
    });
    toast('Peça baixada do estoque', 'success');
    document.getElementById('os-peca-codigo').value = '';
    document.getElementById('os-peca-qtd').value = '1';
    const r = await api(`/ordens-servico/${id}`);
    document.getElementById('os-pecas-lista').innerHTML = osRenderPecas(r.pecas);
    document.getElementById('os-peca-codigo').focus();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function osSalvarEdicao(id) {
  const corpo = {
    tipo_aparelho: document.getElementById('os-ed-tipo').value.trim(),
    marca: document.getElementById('os-ed-marca').value.trim(),
    modelo: document.getElementById('os-ed-modelo').value.trim(),
    numero_serie: document.getElementById('os-ed-serie').value.trim(),
    acessorios: document.getElementById('os-ed-acessorios').value.trim(),
    defeito_declarado: document.getElementById('os-ed-defeito').value.trim(),
    taxa_avaliacao: document.getElementById('os-ed-taxa').value || 0,
    observacao: document.getElementById('os-ed-obs').value.trim(),
  };
  try {
    await api(`/ordens-servico/${id}`, { method: 'PUT', body: JSON.stringify(corpo) });
    toast('OS atualizada', 'success');
    carregarOS();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function osDesagendar(osId, servicoId) {
  if (!confirm('Desagendar esta visita? (técnico/dia errado — some da rota dele)')) return;
  try {
    await api(`/ordens-servico/${osId}/desagendar/${servicoId}`, { method: 'DELETE' });
    toast('Visita desagendada', 'success');
    abrirOSDetalhe(osId);
    carregarOS();
    carregarSeloAgendar(); // pode ter voltado pra 'aguardando_agendamento'
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function osAtualizarStatus(id, status) {
  try {
    await api(`/ordens-servico/${id}`, { method: 'PUT', body: JSON.stringify({ status }) });
    toast('Status atualizado', 'success');
    carregarOS();
    carregarSeloAgendar();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function osAgendar(id) {
  const tecnicoId = document.getElementById('os-agendar-tecnico').value;
  const data = document.getElementById('os-agendar-data').value;
  if (!tecnicoId || !data) {
    toast('Escolha técnico e data', 'error');
    return;
  }
  try {
    await api(`/ordens-servico/${id}/agendar`, {
      method: 'POST', body: JSON.stringify({ tecnico_id: Number(tecnicoId), nova_data: data }),
    });
    toast('Visita agendada', 'success');
    abrirOSDetalhe(id);
    carregarOS();
    carregarSeloAgendar(); // saiu de 'aguardando_agendamento'
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ═══ Cotação: peças aguardando preço, antes de comprar ══════════════════
// Fica ANTES da compra. O técnico ou o Kalebe acham que vão precisar de uma
// peça — por código ou só pelo modelo da máquina — e lançam aqui para levar
// ao fornecedor. Hoje isso é manual (o botão "Abrir GAP" só leva ao portal;
// não há login automatizado confirmado ainda — ver /api/cotacoes/config).
// Depois de cotado, o valor fica registrado; comprar de fato continua sendo
// outra etapa (planilha / aba Peças), esta lista não lança pedido nenhum.
let _cotacoesAtuais = [];
const _brlCotacao = n => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

async function carregarCotacoes() {
  const mount = document.getElementById('cotacao-conteudo');
  if (!mount) return;

  const todas = document.getElementById('cotacao-mostrar-todas')?.checked;
  mount.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:30px;"><div class="spinner"></div> Carregando...</div>`;

  let r;
  try {
    r = await api(`/cotacoes${todas ? '' : '?status=pendente'}`);
  } catch (e) {
    mount.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  _cotacoesAtuais = r.itens || [];
  atualizarSeloCotacao(r.pendentes ?? _cotacoesAtuais.filter(i => i.status === 'pendente').length);
  renderCotacoes(mount, _cotacoesAtuais, todas);
}

// Contagem visível mesmo com a seção fechada — sem isso ninguém lembra de
// abrir pra ver se chegou foto nova do técnico em campo.
function atualizarSeloCotacao(qtd) {
  const selo = document.getElementById('cotacao-selo');
  if (!selo) return;
  selo.hidden = qtd === 0;
  selo.textContent = qtd;
  selo.classList.toggle('accent', qtd > 0);
}

function renderCotacoes(mount, itens, todas) {
  const cabecalho = `
    <p class="pecas-nota-cotacao" style="margin-top:0;">
      Registre aqui peça que o técnico pediu preço mas <b>ainda não foi
      comprada</b>. Assim que você comprar de verdade, ela aparece sozinha
      lá em cima, na lista de "Peças Compradas" — não precisa copiar nada
      daqui pra lá.
    </p>
    <div class="cotacao-form">
      <div class="form-group">
        <label class="form-label">Código da peça</label>
        <input class="form-input" id="cotacao-novo-codigo" placeholder="ex: DE97-01234A">
      </div>
      <div class="form-group">
        <label class="form-label">Modelo da máquina</label>
        <input class="form-input" id="cotacao-novo-modelo" placeholder="ex: NA-F70B6">
      </div>
      <div class="form-group cotacao-desc">
        <label class="form-label">Observação</label>
        <input class="form-input" id="cotacao-novo-obs" placeholder="ex: cliente João, urgente"
               onkeydown="if(event.key==='Enter') adicionarCotacao()">
      </div>
      <div class="form-group cotacao-qtd">
        <label class="form-label">Qtd</label>
        <input class="form-input" type="number" min="1" value="1" id="cotacao-novo-qtd">
      </div>
      <button class="btn btn-primary" onclick="adicionarCotacao()">${icone('plus', 'icone-13')} Adicionar</button>
    </div>`;

  if (itens.length === 0) {
    mount.innerHTML = cabecalho + `
      <div class="historico-vazio">
        ${icone('check', 'icone-24')}
        <p>${todas ? 'Nenhuma cotação registrada ainda.' : 'Nada pendente — todas as peças já foram cotadas.'}</p>
      </div>`;
    return;
  }

  const linhas = itens.map(item => {
    const cotado = item.status === 'cotado';
    const meta = [item.modelo || 'sem modelo', `${Number(item.quantidade || 1)}x`,
                  (item.criado_em || '').split(' ')[0]].filter(Boolean).join(' · ');

    const selo = cotado
      ? `<span class="conc-tag ok">cotado: ${esc(_brlCotacao(item.valor_cotado))}${item.fornecedor ? ' · ' + esc(item.fornecedor) : ''}</span>`
      : `<span class="conc-tag aviso">aguardando cotação</span>`;

    const acoes = cotado
      ? `<div class="cotacao-acoes">
           <button class="btn btn-ghost btn-sm" onclick="reabrirCotacao(${item.id})">Reabrir</button>
           <button class="btn-remove" title="Remover" onclick="removerCotacao(${item.id})">${icone('x', 'icone-11')}</button>
         </div>`
      : `<div class="cotacao-campo cotacao-campo-sm">
           <label class="peca-rot">Valor (R$)</label>
           <input class="form-input" type="number" step="0.01" min="0" id="cotacao-valor-${item.id}"
                  placeholder="0,00" onkeydown="if(event.key==='Enter') marcarCotado(${item.id})">
         </div>
         <div class="cotacao-campo">
           <label class="peca-rot">Fornecedor</label>
           <input class="form-input" id="cotacao-fornecedor-${item.id}" placeholder="ex: GAP Panasonic"
                  onkeydown="if(event.key==='Enter') marcarCotado(${item.id})">
         </div>
         <div class="cotacao-acoes">
           <button class="btn btn-primary btn-sm" onclick="marcarCotado(${item.id})">Marcar cotado</button>
           <button class="btn-remove" title="Remover" onclick="removerCotacao(${item.id})">${icone('x', 'icone-11')}</button>
         </div>`;

    // Foto vem do técnico em campo (desfecho "Cotação de peça") — é dela que
    // sai o modelo/série certo. Miniatura clicável: abre em tamanho real
    // pra ler o que está escrito na etiqueta sem depender de zoom no navegador.
    const foto = item.foto
      ? `<a href="${item.foto}" target="_blank" rel="noopener" class="cotacao-foto-link" title="Ver foto da etiqueta">
           <img class="cotacao-foto-mini" src="${item.foto}" alt="Foto da etiqueta enviada pelo técnico">
         </a>`
      : '';

    return `
      <div class="cotacao-linha${cotado ? ' cotado' : ''}" id="cotacao-${item.id}">
        ${foto}
        <div class="cotacao-ident">
          <span class="cotacao-cod">${esc(item.codigo) || '—'}</span>
          <span class="peca-meta">${esc(meta)}</span>
          ${selo}
        </div>
        <div class="cotacao-campo">
          <label class="peca-rot">Observação</label>
          <input class="form-input" value="${esc(item.descricao)}" placeholder="—"
                 onchange="salvarObsCotacao(${item.id}, this.value)">
        </div>
        ${acoes}
      </div>`;
  }).join('');

  mount.innerHTML = cabecalho + `
    <span class="pecas-contagem" style="display:block;margin-bottom:10px;">
      ${itens.length} item${itens.length !== 1 ? 's' : ''}${!todas ? ' · aguardando cotação' : ''}
    </span>
    ${linhas}
    <button class="btn btn-ghost btn-sm" style="margin-top:6px;" onclick="copiarListaCotacao()">Copiar lista</button>`;
}

async function adicionarCotacao() {
  const codigo = document.getElementById('cotacao-novo-codigo').value.trim();
  const modelo = document.getElementById('cotacao-novo-modelo').value.trim();
  const descricao = document.getElementById('cotacao-novo-obs').value.trim();
  const quantidade = document.getElementById('cotacao-novo-qtd').value || 1;

  if (!codigo && !modelo) {
    toast('Informe o código da peça ou o modelo da máquina', 'error');
    return;
  }

  try {
    await api('/cotacoes', { method: 'POST', body: JSON.stringify({ codigo, modelo, descricao, quantidade }) });
    toast('Item adicionado à lista de cotação', 'success');
    carregarCotacoes();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function marcarCotado(id) {
  const valorEl = document.getElementById(`cotacao-valor-${id}`);
  const fornecedorEl = document.getElementById(`cotacao-fornecedor-${id}`);
  if (!valorEl?.value) {
    toast('Informe o valor cotado', 'error');
    valorEl?.focus();
    return;
  }
  try {
    await api(`/cotacoes/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ status: 'cotado', valor_cotado: valorEl.value, fornecedor: fornecedorEl?.value || '' }),
    });
    toast('Peça marcada como cotada', 'success');
    carregarCotacoes();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function reabrirCotacao(id) {
  try {
    await api(`/cotacoes/${id}`, { method: 'PUT', body: JSON.stringify({ status: 'pendente' }) });
    carregarCotacoes();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function removerCotacao(id) {
  if (!confirm('Remover este item da lista de cotação?')) return;
  try {
    await api(`/cotacoes/${id}`, { method: 'DELETE' });
    toast('Item removido', 'success');
    carregarCotacoes();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function salvarObsCotacao(id, valor) {
  try {
    await api(`/cotacoes/${id}`, { method: 'PUT', body: JSON.stringify({ descricao: valor }) });
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function copiarListaCotacao() {
  const pendentes = _cotacoesAtuais.filter(i => i.status === 'pendente');
  if (pendentes.length === 0) {
    toast('Nada pendente para copiar', 'info');
    return;
  }
  const texto = pendentes.map(item => {
    const partes = [];
    if (item.codigo) partes.push(`Código: ${item.codigo}`);
    if (item.modelo) partes.push(`Modelo: ${item.modelo}`);
    partes.push(`Qtd: ${item.quantidade || 1}`);
    if (item.descricao) partes.push(`Obs: ${item.descricao}`);
    return '- ' + partes.join(' | ');
  }).join('\n');

  try {
    await navigator.clipboard.writeText(texto);
    toast('Lista copiada', 'success');
  } catch {
    toast('Não foi possível copiar automaticamente — selecione o texto na tela', 'error');
  }
}

// ═══ Estoque de peças ══════════════════════════════════════════════════
// O saldo mora AQUI (o AgoraOS não deixa a API escrever estoque). Toda a tela
// bebe de uma cópia local `estoqueCache` para a busca filtrar na hora, sem
// bater no servidor a cada tecla. Só recarrega de verdade depois de mover saldo.
let estoqueCache = [];
let estoqueMovModo = 'entrada'; // entrada | saida | ajuste | editar
let estoqueCatalogo = { aparelhos: [], marcas: [] };
let estoqueFiltroAparelho = ''; // chip ativo; '' = todos
// Navegação em dois níveis: 'raiz' mostra os estoques (prateleiras); 'grupo'
// mostra as peças de um estoque aberto. estoqueGrupos alimenta o <select> do
// modal para escolher em qual estoque a peça entra.
let estoqueView = 'raiz';
let estoqueGrupoAtual = null; // {id, nome} quando dentro de um estoque
let estoqueGrupos = [];

// Recarrega a view que está ativa — usado depois de qualquer escrita para
// refletir sem tirar o senhor de onde estava.
function carregarEstoque() {
  if (estoqueView === 'grupo' && estoqueGrupoAtual) {
    abrirGrupoEstoque(estoqueGrupoAtual.id, estoqueGrupoAtual.nome);
  } else {
    abrirEstoqueRaiz();
  }
}

// ── Nível 1: os estoques (prateleiras) ──────────────────────────────────
async function abrirEstoqueRaiz() {
  estoqueView = 'raiz';
  estoqueGrupoAtual = null;
  const lista = document.getElementById('estoque-lista');
  if (!lista) return;
  document.getElementById('estoque-breadcrumb').innerHTML = '';
  document.getElementById('estoque-titulo').textContent = 'Meus Estoques';
  document.getElementById('estoque-subtitulo').style.display = '';
  document.getElementById('estoque-subtitulo').innerHTML =
    'Cada estoque é uma prateleira sua (Electrolux, Panasonic...). Abra um ' +
    'para ver e adicionar as peças dele. Isso é o saldo de verdade — ' +
    'diferente da aba "Peças", que só concilia compra com cliente.';
  document.getElementById('estoque-topo-acoes').innerHTML = podeUsuario('estoque_editar')
    ? '<button class="btn btn-ghost btn-sm" onclick="abrirBiparNota()">📷 Bipar nota fiscal</button>'
      + '<button class="btn btn-primary btn-sm" onclick="abrirCriarGrupo()">+ Criar estoque</button>'
    : '';
  document.getElementById('estoque-filtros').style.display = 'none';
  document.getElementById('estoque-chips-aparelho').innerHTML = '';
  document.getElementById('estoque-resumo').innerHTML = '';
  lista.innerHTML = '<div class="carregando">Carregando estoques...</div>';
  try {
    const d = await api('/estoque/grupos');
    estoqueGrupos = d.grupos || [];
    renderEstoqueRaiz(d);
  } catch (e) {
    lista.innerHTML = `<div class="erro-box">Não foi possível carregar os estoques: ${esc(e.message)}</div>`;
  }
}

const _brlEstoque = n => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

function _grupoPorId(id) {
  return estoqueGrupos.find(g => String(g.id) === String(id)) || null;
}

// Card de prateleira. Passa SÓ o id (string) no onclick — nunca o nome (aspas
// do nome quebravam o HTML). ag traz os agregados roll-up (subtree inteiro).
function _cardPrateleira(id, nome, ag, cor) {
  const alerta = ag.abaixo_minimo || 0;
  const subs = ag.sub_estoques || 0;
  const metaSub = subs ? `${subs} sub-estoque${subs > 1 ? 's' : ''} · ` : '';
  return `
    <div class="estoque-prateleira" onclick="abrirGrupoEstoque('${id}')"
         style="${cor ? `border-left:4px solid ${esc(cor)};` : ''}">
      <div class="estoque-prateleira-nome">${esc(nome)}${alerta ? `<span class="estoque-tag-alerta">${alerta} em falta</span>` : ''}</div>
      <div class="estoque-prateleira-meta">${metaSub}${ag.total_pecas || 0} ${ag.total_pecas === 1 ? 'peça' : 'peças'} · ${_brlEstoque(ag.valor_investido)}</div>
    </div>`;
}

// Trilha "Meus Estoques › Panasonic › Geladeira" subindo pelos parent_id.
function _breadcrumbEstoque(grupoId) {
  const partes = ['<a onclick="abrirEstoqueRaiz()">Meus Estoques</a>'];
  if (grupoId === 'sem') { partes.push('<span>›</span> Sem estoque'); return partes.join(' '); }
  const cadeia = [];
  let cur = _grupoPorId(grupoId);
  while (cur) { cadeia.unshift(cur); cur = cur.parent_id ? _grupoPorId(cur.parent_id) : null; }
  cadeia.forEach((g, i) => {
    partes.push('<span>›</span>');
    partes.push(i === cadeia.length - 1
      ? esc(g.nome)                                            // atual: sem link
      : `<a onclick="abrirGrupoEstoque('${g.id}')">${esc(g.nome)}</a>`);
  });
  return partes.join(' ');
}

function renderEstoqueRaiz(d) {
  const lista = document.getElementById('estoque-lista');
  document.getElementById('estoque-subgrupos').innerHTML = '';
  // Só os estoques de TOPO (sem pai); os sub-estoques aparecem dentro dos pais.
  const topo = (d.grupos || []).filter(g => !g.parent_id);
  const cards = topo.map(g => _cardPrateleira(g.id, g.nome, g, g.cor)).join('');
  // "Sem estoque" só aparece quando há peça solta — não polui quando está tudo guardado.
  const sem = (d.sem_estoque && d.sem_estoque.total_pecas > 0)
    ? _cardPrateleira('sem', 'Sem estoque', d.sem_estoque, null) : '';
  if (!cards && !sem) {
    lista.innerHTML = '<div class="vazio-box">Nenhum estoque ainda. Clique em <b>+ Criar estoque</b> para começar — ex: Electrolux, Panasonic.</div>';
    return;
  }
  lista.innerHTML = `<div class="estoque-prateleiras">${cards}${sem}</div>`;
}

// ── Nível 2: as peças de um estoque ─────────────────────────────────────
// grupoId chega como string ('3' ou 'sem'). nome é opcional: quando não vem
// (clique no card, que só passa o id), é resolvido a partir de estoqueGrupos.
async function abrirGrupoEstoque(grupoId, nome) {
  grupoId = String(grupoId);
  estoqueView = 'grupo';
  estoqueFiltroAparelho = '';
  const lista = document.getElementById('estoque-lista');
  if (!lista) return;
  lista.innerHTML = '<div class="carregando">Carregando...</div>';
  document.getElementById('estoque-subgrupos').innerHTML = '';

  // Recarrega os grupos SEMPRE ao entrar: garante sub-estoques, breadcrumb e
  // agregados atuais (inclusive depois de criar/mover coisas aqui dentro).
  try {
    const dg = await api('/estoque/grupos');
    estoqueGrupos = dg.grupos || [];
  } catch (e) {
    lista.innerHTML = `<div class="erro-box">Não foi possível carregar os estoques: ${esc(e.message)}</div>`;
    return;
  }

  const ehSem = grupoId === 'sem';
  if (nome == null) nome = ehSem ? 'Sem estoque' : (_grupoPorId(grupoId)?.nome || 'Estoque');
  estoqueGrupoAtual = { id: grupoId, nome };

  document.getElementById('estoque-breadcrumb').innerHTML = _breadcrumbEstoque(grupoId);
  document.getElementById('estoque-titulo').textContent = nome;
  document.getElementById('estoque-subtitulo').style.display = 'none';
  // Peça só entra em SUB-estoque (tem pai). No estoque de topo (Panasonic) a
  // ação é criar sub-estoque; a peça vai dentro dele. Pedido do Kalebe.
  const ehTopo = !ehSem && !(_grupoPorId(grupoId)?.parent_id);
  const podeEd = podeUsuario('estoque_editar'), podeEx = podeUsuario('estoque_excluir');
  const btnAddPeca = '<button class="btn btn-primary btn-sm" onclick="abrirEntradaEstoque()">+ Adicionar peça</button>';
  document.getElementById('estoque-topo-acoes').innerHTML = ehSem
    ? (podeEd ? btnAddPeca : '')
    : `
    ${podeEd && !ehTopo ? btnAddPeca : ''}
    ${podeEd ? `<button class="btn ${ehTopo ? 'btn-primary' : 'btn-ghost'} btn-sm" onclick="abrirCriarSubEstoque()">+ Sub-estoque</button>
    <button class="btn btn-ghost btn-sm" onclick="renomearGrupoAtual()">Renomear</button>` : ''}
    ${podeEx ? '<button class="btn btn-ghost btn-sm" onclick="excluirGrupoAtual()">Excluir estoque</button>' : ''}`;
  document.getElementById('estoque-filtros').style.display = 'flex';

  // Sub-estoques (filhos diretos deste estoque) num container próprio.
  const filhos = ehSem ? [] : estoqueGrupos.filter(g => String(g.parent_id) === grupoId);
  const sg = document.getElementById('estoque-subgrupos');
  sg.innerHTML = filhos.length
    ? `<div class="estoque-subgrupos-titulo">Sub-estoques</div>
       <div class="estoque-prateleiras">${filhos.map(g => _cardPrateleira(g.id, g.nome, g, g.cor)).join('')}</div>
       <div class="estoque-subgrupos-titulo">Peças aqui</div>`
    : '';

  // Peças diretas deste estoque.
  try {
    const q = ehSem ? 'grupo_id=sem' : `grupo_id=${encodeURIComponent(grupoId)}`;
    const d = await api('/estoque?' + q);
    estoqueCache = d.itens || [];
    estoqueCatalogo = { aparelhos: d.aparelhos || [], marcas: d.marcas || [] };
    renderEstoqueResumo(d);
    montarFiltrosEstoque();
    filtrarEstoque();
  } catch (e) {
    lista.innerHTML = `<div class="erro-box">Não foi possível carregar as peças: ${esc(e.message)}</div>`;
  }
}

// Preenche o select de marca, os chips de aparelho e os datalists do modal a
// partir do que já existe cadastrado — sem inventar categoria, só reaproveita.
function montarFiltrosEstoque() {
  const sel = document.getElementById('estoque-filtro-marca');
  if (sel) {
    const atual = sel.value;
    sel.innerHTML = '<option value="">Todas as marcas</option>' +
      estoqueCatalogo.marcas.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
    sel.value = atual; // preserva a escolha entre recargas
  }
  const chips = document.getElementById('estoque-chips-aparelho');
  if (chips) {
    if (!estoqueCatalogo.aparelhos.length && !estoqueFiltroAparelho) {
      chips.innerHTML = '';
    } else {
      const btn = (val, rot) =>
        `<button class="estoque-chip ${estoqueFiltroAparelho === val ? 'ativo' : ''}" onclick='filtrarPorAparelho(${JSON.stringify(val)})'>${esc(rot)}</button>`;
      chips.innerHTML = btn('', 'Todos') + estoqueCatalogo.aparelhos.map(a => btn(a, a)).join('');
    }
  }
  const dlA = document.getElementById('estoque-datalist-aparelho');
  if (dlA) dlA.innerHTML = estoqueCatalogo.aparelhos.map(a => `<option value="${esc(a)}">`).join('');
  const dlM = document.getElementById('estoque-datalist-marca');
  if (dlM) dlM.innerHTML = estoqueCatalogo.marcas.map(m => `<option value="${esc(m)}">`).join('');
}

function filtrarPorAparelho(val) {
  estoqueFiltroAparelho = val;
  montarFiltrosEstoque(); // reflete o chip ativo
  filtrarEstoque();
}

function renderEstoqueResumo(d) {
  const resumo = document.getElementById('estoque-resumo');
  if (!resumo) return;
  const investido = (d.valor_investido || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const alerta = d.abaixo_minimo || 0;
  resumo.innerHTML = `
    <div class="estoque-card">
      <div class="estoque-card-num">${d.total_itens || 0}</div>
      <div class="estoque-card-lbl">peças cadastradas</div>
    </div>
    <div class="estoque-card">
      <div class="estoque-card-num">${investido}</div>
      <div class="estoque-card-lbl">investido em estoque</div>
    </div>
    <div class="estoque-card ${alerta ? 'estoque-card--alerta' : ''}">
      <div class="estoque-card-num">${alerta}</div>
      <div class="estoque-card-lbl">${alerta === 1 ? 'peça abaixo do mínimo' : 'peças abaixo do mínimo'}</div>
    </div>`;
}

function filtrarEstoque() {
  const termo = (document.getElementById('estoque-busca-input')?.value || '').trim().toLowerCase();
  const marca = (document.getElementById('estoque-filtro-marca')?.value || '').toLowerCase();
  let itens = estoqueCache;
  if (termo) itens = itens.filter(i =>
    (i.codigo || '').toLowerCase().includes(termo) ||
    (i.descricao || '').toLowerCase().includes(termo) ||
    (i.marca || '').toLowerCase().includes(termo) ||
    (i.modelo || '').toLowerCase().includes(termo));
  if (marca) itens = itens.filter(i => (i.marca || '').toLowerCase() === marca);
  if (estoqueFiltroAparelho) itens = itens.filter(i => (i.aparelho || '') === estoqueFiltroAparelho);
  renderEstoqueLista(itens);
}

function _cardEstoque(i) {
  const brl = n => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const g = n => (Number(n) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 3 });
  const alerta = i.abaixo_minimo;
  // Linha de identidade: marca · modelo (o aparelho já é o cabeçalho do grupo).
  const ident = [i.marca, i.modelo].map(x => (x || '').trim()).filter(Boolean).join(' · ');
  const venda = Number(i.preco_venda) > 0 ? ` · venda ${brl(i.preco_venda)}` : '';
  return `
    <div class="estoque-item ${alerta ? 'estoque-item--alerta' : ''}">
      <div class="estoque-item-info">
        <div class="estoque-item-cod">${esc(i.codigo)}${ident ? `<span class="estoque-item-ident">${esc(ident)}</span>` : ''}${alerta ? '<span class="estoque-tag-alerta">abaixo do mínimo</span>' : ''}</div>
        <div class="estoque-item-desc">${esc(i.descricao || 'Sem descrição')}</div>
        <div class="estoque-item-meta">
          custo médio ${brl(i.custo_medio)} · vale ${brl(i.valor_total)}${venda}${Number(i.minimo) > 0 ? ` · mínimo ${g(i.minimo)}` : ''}
        </div>
      </div>
      <div class="estoque-item-saldo">
        <div class="estoque-saldo-num">${g(i.saldo)}</div>
        <div class="estoque-saldo-lbl">em estoque</div>
      </div>
      <div class="estoque-item-acoes">
        ${podeUsuario('estoque_editar') ? `
        <button class="btn btn-ghost btn-xs" title="Dar saída" onclick='abrirSaidaEstoque(${JSON.stringify(i.codigo)}, ${JSON.stringify(i.descricao || "")})'>− Saída</button>
        <button class="btn btn-ghost btn-xs" title="Entrada" onclick='abrirEntradaEstoque(${JSON.stringify(i.codigo)}, ${JSON.stringify(i.descricao || "")})'>+ Entrada</button>
        <button class="btn btn-ghost btn-xs" title="Editar peça (marca, aparelho, modelo, preço)" onclick='abrirEditarEstoque(${JSON.stringify(i)})'>Editar</button>
        <button class="btn btn-ghost btn-xs" title="Corrigir saldo pela contagem física" onclick='abrirAjusteEstoque(${i.id}, ${JSON.stringify(i.codigo)}, ${Number(i.saldo) || 0})'>Ajustar</button>
        <button class="btn btn-ghost btn-xs" title="Definir estoque mínimo" onclick='definirMinimoEstoque(${i.id}, ${JSON.stringify(i.codigo)}, ${Number(i.minimo) || 0})'>Mínimo</button>` : ''}
        <button class="btn btn-ghost btn-xs" title="Histórico de movimentos" onclick='verHistoricoEstoque(${i.id}, ${JSON.stringify(i.codigo)})'>Histórico</button>
        ${podeUsuario('estoque_excluir') ? `<button class="btn btn-ghost btn-xs estoque-btn-excluir" title="Excluir a peça do estoque" onclick='excluirPecaEstoque(${i.id}, ${JSON.stringify(i.codigo)})'>Excluir</button>` : ''}
      </div>
    </div>`;
}

function renderEstoqueLista(itens) {
  const lista = document.getElementById('estoque-lista');
  if (!lista) return;
  if (!itens.length) {
    lista.innerHTML = estoqueCache.length
      ? '<div class="vazio-box">Nenhuma peça encontrada para esse filtro.</div>'
      : '<div class="vazio-box">Nenhuma peça no estoque ainda. Clique em <b>Dar entrada</b> para começar.</div>';
    return;
  }
  // Agrupado por aparelho, igual às prateleiras do AgoraOS. Peça sem aparelho
  // cai num grupo "Sem categoria" no fim, para não sumir da vista.
  const grupos = new Map();
  itens.forEach(i => {
    const chave = (i.aparelho || '').trim() || 'Sem categoria';
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave).push(i);
  });
  const ordenadas = [...grupos.keys()].sort((a, b) => {
    if (a === 'Sem categoria') return 1;
    if (b === 'Sem categoria') return -1;
    return a.localeCompare(b, 'pt-BR');
  });
  lista.innerHTML = ordenadas.map(nome => {
    const doGrupo = grupos.get(nome);
    return `
    <div class="estoque-grupo">
      <div class="estoque-grupo-cab">
        <span class="estoque-grupo-nome">${esc(nome)}</span>
        <span class="estoque-grupo-cont">${doGrupo.length} ${doGrupo.length === 1 ? 'peça' : 'peças'}</span>
      </div>
      ${doGrupo.map(_cardEstoque).join('')}
    </div>`;
  }).join('');
}

// Mostra/esconde os blocos do modal conforme o modo. Uma config por grupo é
// mais legível que dez linhas de style.display espalhadas em cada função.
function _visibilidadeModalEstoque(cfg) {
  const grupos = {
    codigo:    'estoque-mov-grupo-codigo',
    desc:      'estoque-mov-grupo-desc',
    estoque:   'estoque-mov-grupo-estoque',
    cliente:   'estoque-mov-grupo-cliente',
    categoria: 'estoque-mov-grupo-categoria',
    modelo:    'estoque-mov-grupo-modelo',
    qtdcusto:  'estoque-mov-grupo-qtd-custo',
    custo:     'estoque-mov-grupo-custo',
    obs:       'estoque-mov-grupo-obs',
  };
  for (const [chave, id] of Object.entries(grupos)) {
    const el = document.getElementById(id);
    if (el) el.style.display = cfg[chave] ? '' : 'none';
  }
}

// Preenche o <select> de estoque do modal com as prateleiras existentes e
// deixa a escolhida marcada. Vazio = "Sem estoque".
function _popularSelectEstoque(selecionado) {
  const sel = document.getElementById('estoque-mov-estoque');
  if (!sel) return;
  // Ordena em árvore e indenta os sub-estoques, para dar pra escolher
  // "Panasonic › Geladeira" sem confundir com uma "Geladeira" de outro pai.
  const filhos = {};
  estoqueGrupos.forEach(g => { (filhos[g.parent_id || 0] = filhos[g.parent_id || 0] || []).push(g); });
  const opts = [];
  const caminhar = (paiId, nivel) => {
    (filhos[paiId] || []).sort((a, b) => (a.nome || '').localeCompare(b.nome || '', 'pt-BR'))
      .forEach(g => {
        const prefixo = nivel ? '  '.repeat(nivel) + '› ' : '';
        opts.push(`<option value="${g.id}">${prefixo}${esc(g.nome)}</option>`);
        caminhar(g.id, nivel + 1);
      });
  };
  caminhar(0, 0);
  sel.innerHTML = '<option value="">Sem estoque</option>' + opts.join('');
  sel.value = selecionado != null ? String(selecionado) : '';
}

function _limparCamposEstoque() {
  ['codigo', 'desc', 'aparelho', 'marca', 'modelo', 'preco', 'qtd', 'custo', 'obs', 'cliente', 'referencia']
    .forEach(c => { const el = document.getElementById('estoque-mov-' + c); if (el) el.value = ''; });
  const sel = document.getElementById('estoque-mov-estoque');
  if (sel) sel.value = '';
}

// Clientes dos atendimentos para o autocomplete do "saiu para quem".
// Buscado uma vez e reaproveitado — não muda a cada abertura do modal.
let estoqueClientesCarregado = false;
async function _carregarClientesAtendimento() {
  if (estoqueClientesCarregado) return;
  try {
    const d = await api('/estoque/atendimentos');
    const dl = document.getElementById('estoque-datalist-cliente');
    if (dl) dl.innerHTML = (d.clientes || []).map(c => `<option value="${esc(c)}">`).join('');
    estoqueClientesCarregado = true;
  } catch { /* autocomplete é conveniência; sem ele ainda dá para digitar */ }
}

function _labelQtd(txt) {
  document.getElementById('estoque-mov-qtd').closest('.form-group').querySelector('label').textContent = txt;
}

function abrirEntradaEstoque(codigo = '', desc = '') {
  estoqueMovModo = 'entrada';
  _limparCamposEstoque();
  const existente = codigo ? estoqueCache.find(i => i.codigo === codigo) : null;
  document.getElementById('estoque-mov-titulo').textContent = codigo ? `Entrada — ${codigo}` : 'Dar entrada';
  document.getElementById('estoque-mov-codigo-fixo').value = codigo;
  document.getElementById('estoque-mov-codigo').value = codigo;
  document.getElementById('estoque-mov-desc').value = desc;
  // Qual estoque já vem selecionado: o da peça existente, senão o que o senhor
  // está com aberto na tela (adicionar peça "aqui dentro"). 'sem' = nenhum.
  let grupoPre = '';
  if (existente) grupoPre = existente.grupo_id || '';
  else if (estoqueGrupoAtual && estoqueGrupoAtual.id !== 'sem') grupoPre = estoqueGrupoAtual.id;
  _popularSelectEstoque(grupoPre);
  // Peça já existente entra com a categoria preenchida, para poder completar/corrigir.
  if (existente) {
    document.getElementById('estoque-mov-aparelho').value = existente.aparelho || '';
    document.getElementById('estoque-mov-marca').value = existente.marca || '';
    document.getElementById('estoque-mov-modelo').value = existente.modelo || '';
    document.getElementById('estoque-mov-preco').value = Number(existente.preco_venda) > 0 ? existente.preco_venda : '';
  }
  _visibilidadeModalEstoque({ codigo: !codigo, desc: true, estoque: true, categoria: true, modelo: true, qtdcusto: true, custo: true, obs: true });
  _labelQtd('Quantidade');
  document.getElementById('modal-estoque-mov').classList.add('open');
  setTimeout(() => document.getElementById(codigo ? 'estoque-mov-qtd' : 'estoque-mov-codigo').focus(), 80);
}

function abrirSaidaEstoque(codigo, desc = '') {
  estoqueMovModo = 'saida';
  _limparCamposEstoque();
  _carregarClientesAtendimento(); // preenche o datalist de clientes em paralelo
  document.getElementById('estoque-mov-titulo').textContent = `Saída — ${codigo}`;
  document.getElementById('estoque-mov-codigo-fixo').value = codigo;
  _visibilidadeModalEstoque({ cliente: true, qtdcusto: true, custo: false, obs: true });
  _labelQtd('Quantidade a dar baixa');
  document.getElementById('modal-estoque-mov').classList.add('open');
  setTimeout(() => document.getElementById('estoque-mov-qtd').focus(), 80);
}

function abrirAjusteEstoque(id, codigo, saldoAtual) {
  estoqueMovModo = 'ajuste';
  _limparCamposEstoque();
  document.getElementById('estoque-mov-titulo').textContent = `Ajustar saldo — ${codigo}`;
  document.getElementById('estoque-mov-codigo-fixo').value = id;
  _visibilidadeModalEstoque({ qtdcusto: true, custo: false, obs: true });
  _labelQtd('Saldo real contado');
  document.getElementById('estoque-mov-qtd').value = saldoAtual;
  document.getElementById('modal-estoque-mov').classList.add('open');
  setTimeout(() => document.getElementById('estoque-mov-qtd').select(), 80);
}

// Editar a FICHA da peça (marca, aparelho, modelo, descrição, preço) sem tocar
// no saldo — é aqui que se "marca" uma peça como geladeira depois de cadastrada.
function abrirEditarEstoque(item) {
  estoqueMovModo = 'editar';
  _limparCamposEstoque();
  document.getElementById('estoque-mov-titulo').textContent = `Editar — ${item.codigo}`;
  document.getElementById('estoque-mov-codigo-fixo').value = item.id;
  document.getElementById('estoque-mov-desc').value = item.descricao || '';
  document.getElementById('estoque-mov-aparelho').value = item.aparelho || '';
  document.getElementById('estoque-mov-marca').value = item.marca || '';
  document.getElementById('estoque-mov-modelo').value = item.modelo || '';
  document.getElementById('estoque-mov-preco').value = Number(item.preco_venda) > 0 ? item.preco_venda : '';
  _popularSelectEstoque(item.grupo_id || '');
  _visibilidadeModalEstoque({ desc: true, estoque: true, categoria: true, modelo: true, obs: false });
  document.getElementById('modal-estoque-mov').classList.add('open');
  setTimeout(() => document.getElementById('estoque-mov-aparelho').focus(), 80);
}

async function salvarMovEstoque() {
  const btn = document.getElementById('estoque-mov-salvar');
  const val = id => document.getElementById(id).value;
  const obs = val('estoque-mov-obs').trim() || null;
  const fixo = val('estoque-mov-codigo-fixo');
  // grupo_id do <select>: '' vira null (Sem estoque). Sempre enviado nos modos
  // que mostram o seletor, para o servidor saber que é uma escolha explícita.
  const grupoSel = val('estoque-mov-estoque');
  const cat = () => ({
    aparelho: val('estoque-mov-aparelho').trim(),
    marca: val('estoque-mov-marca').trim(),
    modelo: val('estoque-mov-modelo').trim(),
    preco_venda: parseFloat(val('estoque-mov-preco')) || 0,
    grupo_id: grupoSel ? Number(grupoSel) : null,
  });

  // Só entrada/saída/ajuste exigem quantidade; editar não mexe em saldo.
  const qtd = parseFloat(val('estoque-mov-qtd'));
  if (estoqueMovModo !== 'editar' &&
      (!isFinite(qtd) || (estoqueMovModo !== 'ajuste' && qtd <= 0))) {
    toast('Informe uma quantidade válida.', 'error');
    return;
  }
  btn.disabled = true;
  try {
    if (estoqueMovModo === 'entrada') {
      const codigo = (fixo || val('estoque-mov-codigo')).trim();
      if (!codigo) { toast('Informe o código da peça.', 'error'); btn.disabled = false; return; }
      const referencia = val('estoque-mov-referencia').trim();
      const custo_unit = parseFloat(val('estoque-mov-custo')) || 0;
      if (referencia) {
        // Entrada carimbada com a nota fiscal: usa o endpoint idempotente, que
        // não duplica se a mesma nota já tiver lançado esta peça.
        const c = cat();
        const rn = await api('/estoque/entrada-nota', { method: 'POST', body: JSON.stringify({
          referencia, grupo_id: c.grupo_id,
          itens: [{ codigo, descricao: val('estoque-mov-desc').trim(), quantidade: qtd, custo_unit }] }) });
        toast('Entrada da nota no estoque.', 'success');
        osAvisarEsperando((rn.resultados || []).flatMap(x => x.os_esperando || []));
      } else {
        const re = await api('/estoque/entrada', { method: 'POST', body: JSON.stringify({
          codigo, descricao: val('estoque-mov-desc').trim(),
          quantidade: qtd, custo_unit, obs, ...cat() }) });
        toast('Entrada registrada.', 'success');
        osAvisarEsperando(re.os_esperando);
      }
    } else if (estoqueMovModo === 'saida') {
      await api('/estoque/saida', { method: 'POST', body: JSON.stringify({
        codigo: fixo, quantidade: qtd, obs,
        cliente: val('estoque-mov-cliente').trim() || null }) });
      toast('Saída registrada.', 'success');
    } else if (estoqueMovModo === 'ajuste') {
      await api(`/estoque/${fixo}`, { method: 'PUT', body: JSON.stringify({
        saldo_contado: qtd, obs }) });
      toast('Saldo ajustado.', 'success');
    } else { // editar — só a ficha, sem saldo
      await api(`/estoque/${fixo}`, { method: 'PUT', body: JSON.stringify({
        descricao: val('estoque-mov-desc').trim(), ...cat() }) });
      toast('Peça atualizada.', 'success');
    }
    fecharModais();
    carregarEstoque();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ── Criar / renomear / excluir estoque (prateleira) ─────────────────────
function abrirCriarGrupo() {
  document.getElementById('estoque-grupo-titulo').textContent = 'Criar estoque';
  document.getElementById('estoque-grupo-salvar').textContent = 'Criar';
  document.getElementById('estoque-grupo-id').value = '';
  document.getElementById('estoque-grupo-parent').value = '';   // topo
  document.getElementById('estoque-grupo-nome').value = '';
  document.getElementById('modal-estoque-grupo').classList.add('open');
  setTimeout(() => document.getElementById('estoque-grupo-nome').focus(), 80);
}

// Criar um sub-estoque DENTRO do estoque aberto (Panasonic > Geladeira).
function abrirCriarSubEstoque() {
  if (!estoqueGrupoAtual || estoqueGrupoAtual.id === 'sem') return;
  document.getElementById('estoque-grupo-titulo').textContent = `Novo sub-estoque em ${estoqueGrupoAtual.nome}`;
  document.getElementById('estoque-grupo-salvar').textContent = 'Criar';
  document.getElementById('estoque-grupo-id').value = '';
  document.getElementById('estoque-grupo-parent').value = estoqueGrupoAtual.id;
  document.getElementById('estoque-grupo-nome').value = '';
  document.getElementById('modal-estoque-grupo').classList.add('open');
  setTimeout(() => document.getElementById('estoque-grupo-nome').focus(), 80);
}

function renomearGrupoAtual() {
  if (!estoqueGrupoAtual || estoqueGrupoAtual.id === 'sem') return;
  document.getElementById('estoque-grupo-titulo').textContent = 'Renomear estoque';
  document.getElementById('estoque-grupo-salvar').textContent = 'Salvar';
  document.getElementById('estoque-grupo-id').value = estoqueGrupoAtual.id;
  document.getElementById('estoque-grupo-parent').value = '';
  document.getElementById('estoque-grupo-nome').value = estoqueGrupoAtual.nome;
  document.getElementById('modal-estoque-grupo').classList.add('open');
  setTimeout(() => document.getElementById('estoque-grupo-nome').select(), 80);
}

async function salvarGrupoEstoque() {
  const btn = document.getElementById('estoque-grupo-salvar');
  const id = document.getElementById('estoque-grupo-id').value;
  const parent = document.getElementById('estoque-grupo-parent').value;
  const nome = document.getElementById('estoque-grupo-nome').value.trim();
  if (!nome) { toast('Dê um nome ao estoque.', 'error'); return; }
  btn.disabled = true;
  try {
    if (id) {
      await api(`/estoque/grupos/${id}`, { method: 'PUT', body: JSON.stringify({ nome }) });
      if (estoqueGrupoAtual) estoqueGrupoAtual.nome = nome; // reflete no cabeçalho
      toast('Estoque renomeado.', 'success');
    } else {
      await api('/estoque/grupos', { method: 'POST', body: JSON.stringify({
        nome, parent_id: parent ? Number(parent) : null }) });
      toast(parent ? 'Sub-estoque criado.' : 'Estoque criado.', 'success');
    }
    fecharModais();
    carregarEstoque();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function excluirGrupoAtual() {
  if (!estoqueGrupoAtual || estoqueGrupoAtual.id === 'sem') return;
  // Confirma porque some da lista; mas tranquiliza: nada de dentro se perde.
  if (!confirm(`Excluir o estoque "${estoqueGrupoAtual.nome}"?\n\nAs peças voltam para "Sem estoque" e os sub-estoques sobem um nível — nada é apagado.`)) return;
  try {
    const r = await api(`/estoque/grupos/${estoqueGrupoAtual.id}`, { method: 'DELETE' });
    const n = r.pecas_soltas || 0, s = r.sub_estoques_movidos || 0;
    const partes = [];
    if (n) partes.push(`${n} ${n === 1 ? 'peça voltou' : 'peças voltaram'} para "Sem estoque"`);
    if (s) partes.push(`${s} sub-estoque${s > 1 ? 's subiram' : ' subiu'} de nível`);
    toast('Estoque excluído' + (partes.length ? '. ' + partes.join('; ') + '.' : '.'), 'success');
    // Volta para o pai (se era sub-estoque) ou para a raiz.
    const pai = _grupoPorId(estoqueGrupoAtual.id)?.parent_id;
    if (pai) abrirGrupoEstoque(String(pai)); else abrirEstoqueRaiz();
  } catch (e) { toast(e.message, 'error'); }
}

async function excluirPecaEstoque(id, codigo) {
  // Apaga a peça E todo o histórico dela — some de vez. Por isso confirma.
  // Para peça que só ACABOU (saldo 0) o certo é deixar; isto é para peça
  // cadastrada por engano ou que não se quer mais rastrear.
  if (!confirm(`Excluir a peça ${codigo} do estoque?\n\nApaga também o histórico dela. Não dá para desfazer.`)) return;
  try {
    await api(`/estoque/${id}`, { method: 'DELETE' });
    toast('Peça excluída.', 'success');
    carregarEstoque();
  } catch (e) { toast(e.message, 'error'); }
}

async function definirMinimoEstoque(id, codigo, atual) {
  const v = prompt(`Estoque mínimo de ${codigo}\n\nAvisa quando o saldo chegar nesse número ou abaixo. Zero desliga o aviso.`, atual);
  if (v === null) return;
  const num = parseFloat(String(v).replace(',', '.'));
  if (!isFinite(num) || num < 0) { toast('Número inválido.', 'error'); return; }
  try {
    await api(`/estoque/${id}`, { method: 'PUT', body: JSON.stringify({ minimo: num }) });
    toast('Mínimo definido.', 'success');
    carregarEstoque();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Bipar nota fiscal: lê a chave da NF-e e joga as peças no estoque ─────
let biparItens = [];   // itens resolvidos da nota, aguardando confirmação
let biparChave = '';   // chave da nota (vira a referência idempotente)
let biparNavId = null; // pasta atual no navegador de destino (null = raiz)
let _biparCamera = null; // stream da câmera, para poder desligar

async function abrirBiparNota() {
  biparItens = []; biparChave = '';
  biparNavId = null;
  // Recarrega os estoques SEMPRE: o navegador de destino precisa dos
  // sub-estoques atuais (o senhor pode ter criado um agora há pouco).
  try { estoqueGrupos = (await api('/estoque/grupos')).grupos || []; } catch { /* segue */ }
  document.getElementById('bipar-chave').value = '';
  document.getElementById('bipar-xml').value = '';
  document.getElementById('bipar-xml-area').style.display = 'none';
  document.getElementById('bipar-resultado').innerHTML = '';
  document.getElementById('bipar-confirmar-btn').style.display = 'none';
  // Câmera só quando o navegador sabe ler código de barras nativamente
  // (Android/Chrome). Sem isso, o leitor físico ou a digitação cobrem.
  const temCamera = ('BarcodeDetector' in window) && navigator.mediaDevices?.getUserMedia;
  document.getElementById('bipar-camera-btn').style.display = temCamera ? '' : 'none';
  document.getElementById('modal-estoque-bipar').classList.add('open');
  setTimeout(() => document.getElementById('bipar-chave').focus(), 80);
}

function fecharBiparNota() {
  _pararCameraBipar();
  document.getElementById('modal-estoque-bipar').classList.remove('open');
}

function toggleXmlBipar() {
  const a = document.getElementById('bipar-xml-area');
  a.style.display = a.style.display === 'none' ? 'block' : 'none';
  if (a.style.display !== 'none') document.getElementById('bipar-xml').focus();
}

async function lerNotaBipada() {
  const chave = document.getElementById('bipar-chave').value.trim();
  const xml = document.getElementById('bipar-xml').value.trim();
  if (!chave && !xml) { toast('Bipe a nota ou cole a chave/XML.', 'error'); return; }
  const btn = document.getElementById('bipar-ler-btn');
  btn.disabled = true;
  document.getElementById('bipar-resultado').innerHTML = '<div class="carregando">Lendo a nota...</div>';
  try {
    const d = await api('/estoque/nota/itens', { method: 'POST',
      body: JSON.stringify({ chave, xml }) });
    _pararCameraBipar();
    renderResultadoBipar(d);
  } catch (e) {
    document.getElementById('bipar-resultado').innerHTML = `<div class="erro-box">${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
}

function renderResultadoBipar(d) {
  biparItens = d.itens || [];
  biparChave = d.chave || '';
  const alvo = document.getElementById('bipar-resultado');
  const confirmar = document.getElementById('bipar-confirmar-btn');

  if (!biparItens.length) {
    confirmar.style.display = 'none';
    // Mensagem honesta conforme o motivo do vazio.
    let dica;
    if (d.erro_busca) {
      dica = 'Não consegui ler a nota pelo e-mail agora (demorou ou está indisponível). Cole o XML da nota abaixo.'
           + (d.motivo ? `\n\nDetalhe: ${d.motivo}` : '');
      // Abre o campo de XML na hora — é o caminho de saída.
      const area = document.getElementById('bipar-xml-area');
      if (area) area.style.display = 'block';
    } else if (d.nao_encontrada) {
      dica = d.imap_configurado
        ? 'Essa nota ainda não chegou no e-mail da Panasonic (ou não é dela). Se tiver o XML, cole abaixo.'
        : 'A leitura por chave depende do e-mail configurado. Por enquanto, cole o XML da nota abaixo.';
    } else {
      dica = 'Não encontrei peças nessa nota.';
    }
    alvo.innerHTML = `<div class="vazio-box">${esc(dica)}</div>`;
    return;
  }

  const brl = n => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const g = n => (Number(n) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 3 });
  const linhas = biparItens.map(i => `
    <tr>
      <td><b>${esc(i.codigo)}</b></td>
      <td>${esc(i.descricao || '—')}</td>
      <td style="text-align:right;">${g(i.quantidade)}</td>
      <td style="text-align:right;">${brl(i.custo_unit)}</td>
    </tr>`).join('');
  alvo.innerHTML = `
    <div class="bipar-cabecalho">
      <span class="conc-tag ok">${biparItens.length} peça(s) na nota</span>
      ${biparChave ? `<span class="bipar-chave-tag">NF ...${esc(biparChave.slice(-8))}</span>` : ''}
      ${d.fonte === 'xml' ? '<span class="conc-tag neutro">do XML</span>' : ''}
    </div>
    <div class="estoque-hist-scroll" style="margin-top:8px;">
      <table class="estoque-hist-tabela">
        <thead><tr><th>Código</th><th>Descrição</th><th style="text-align:right;">Qtd</th><th style="text-align:right;">Custo un.</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>
    <div class="bipar-nav-wrap">
      <div class="bipar-nav-titulo">Onde guardar? Entre no estoque e escolha o sub-estoque.</div>
      <div id="bipar-nav"></div>
    </div>`;
  biparNavId = null;      // começa na raiz (Meus Estoques)
  renderBiparNav();
}

// Navegador de destino do bipar: clica na Panasonic, vê os sub-estoques dela,
// clica na Geladeira. A peça só pode ser guardada num sub-estoque (tem pai) —
// mesma regra do estoque; por isso o botão de confirmar só liga aí.
function _filhosEstoqueDe(paiId) {
  return estoqueGrupos
    .filter(g => (g.parent_id || null) === (paiId || null))
    .sort((a, b) => (a.nome || '').localeCompare(b.nome || '', 'pt-BR'));
}

function biparNavegar(id) {
  biparNavId = id;         // null = raiz; senão o id (número) da pasta atual
  renderBiparNav();
}

function renderBiparNav() {
  const nav = document.getElementById('bipar-nav');
  if (!nav) return;

  // Trilha de volta.
  const cadeia = [];
  let cur = biparNavId ? _grupoPorId(biparNavId) : null;
  while (cur) { cadeia.unshift(cur); cur = cur.parent_id ? _grupoPorId(cur.parent_id) : null; }
  const bc = ['<a onclick="biparNavegar(null)">Estoques</a>']
    .concat(cadeia.map((x, i) => '<span>›</span> ' + (i === cadeia.length - 1
      ? esc(x.nome)
      : `<a onclick="biparNavegar(${x.id})">${esc(x.nome)}</a>`)))
    .join(' ');

  // Filhos da pasta atual, como botões (drilla ao clicar).
  const filhos = _filhosEstoqueDe(biparNavId);
  const cards = filhos.map(g => `
    <button class="bipar-nav-item ${String(g.id) === String(biparNavId) ? '' : ''}" onclick="biparNavegar(${g.id})">
      <span>${esc(g.nome)}</span>
      ${g.sub_estoques ? '<span class="bipar-nav-seta">›</span>' : ''}
    </button>`).join('') || '<div class="bipar-nav-vazio">Nenhum sub-estoque aqui.</div>';

  const atual = biparNavId ? _grupoPorId(biparNavId) : null;
  const valido = !!(atual && atual.parent_id != null);   // destino = sub-estoque
  const destino = atual
    ? (valido ? `Vai para <b>${esc(atual.nome)}</b>` : 'Entre num sub-estoque para poder guardar aqui')
    : 'Clique num estoque acima';

  nav.innerHTML = `
    <div class="bipar-nav-bc">${bc}</div>
    <div class="bipar-nav-grid">${cards}</div>
    <div class="bipar-nav-destino ${valido ? 'ok' : ''}">${destino}</div>`;

  document.getElementById('bipar-confirmar-btn').style.display = valido ? '' : 'none';
}

async function confirmarEntradaNota() {
  if (!biparItens.length) return;
  const atual = biparNavId ? _grupoPorId(biparNavId) : null;
  if (!atual || atual.parent_id == null) {
    toast('Entre num sub-estoque para guardar as peças.', 'error');
    return;
  }
  const btn = document.getElementById('bipar-confirmar-btn');
  btn.disabled = true;
  try {
    const r = await api('/estoque/entrada-nota', { method: 'POST', body: JSON.stringify({
      referencia: biparChave || null,
      grupo_id: Number(biparNavId),
      itens: biparItens,
    }) });
    toast(r.mensagem || 'Peças no estoque.', 'success');
    osAvisarEsperando((r.resultados || []).flatMap(x => x.os_esperando || []));
    fecharBiparNota();
    carregarEstoque();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// Leitura pela câmera (progressivo — só onde o BarcodeDetector existe).
async function biparPelaCamera() {
  const video = document.getElementById('bipar-video');
  try {
    const detector = new BarcodeDetector({ formats: ['code_128', 'qr_code'] });
    _biparCamera = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    video.srcObject = _biparCamera;
    video.style.display = 'block';
    await video.play();
    const tick = async () => {
      if (!_biparCamera) return; // câmera desligada: para o laço
      try {
        const cods = await detector.detect(video);
        const achou = cods.map(c => c.rawValue).find(v => /\d{44}/.test(v));
        if (achou) {
          document.getElementById('bipar-chave').value = achou;
          lerNotaBipada();
          return;
        }
      } catch { /* frame ruim: tenta o próximo */ }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  } catch (e) {
    toast('Não consegui abrir a câmera. Use o leitor ou digite a chave.', 'error');
    _pararCameraBipar();
  }
}

function _pararCameraBipar() {
  if (_biparCamera) { _biparCamera.getTracks().forEach(t => t.stop()); _biparCamera = null; }
  const v = document.getElementById('bipar-video');
  if (v) { v.srcObject = null; v.style.display = 'none'; }
}

async function verHistoricoEstoque(id, codigo) {
  try {
    const d = await api(`/estoque/${id}/historico`);
    const brl = n => n == null ? '—' : (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    const g = n => (Number(n) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 3 });
    const rotulo = { entrada: '↑ entrada', saida: '↓ saída', ajuste: '⚙ ajuste' };
    // "Origem/destino": mostra de onde veio ou para quem foi. A referência é o
    // cliente (na saída) ou a nota (na entrada) — é o elo com o resto do sistema.
    const origemDestino = m => {
      const ref = (m.referencia || '').trim();
      if (m.origem === 'atendimento') return ref ? `→ ${esc(ref)}` : 'atendimento';
      if (m.origem === 'nota') return ref ? `nota ${esc(ref)}` : 'nota fiscal';
      return esc(m.origem || '—');
    };
    const linhas = (d.movimentos || []).map(m => `
      <tr class="estoque-hist-${esc(m.tipo)}">
        <td>${esc(rotulo[m.tipo] || m.tipo)}</td>
        <td style="text-align:right;">${m.tipo === 'saida' ? '−' : (m.tipo === 'ajuste' && m.quantidade < 0 ? '' : '+')}${g(Math.abs(m.quantidade))}</td>
        <td style="text-align:right;">${g(m.saldo_apos)}</td>
        <td style="text-align:right;">${brl(m.custo_unit)}</td>
        <td>${origemDestino(m)}</td>
        <td>${esc(m.autor || '—')}</td>
        <td>${esc(formatarDataHora(m.criado_em))}</td>
        <td>${esc(m.obs || '')}</td>
      </tr>`).join('');
    const corpo = linhas || '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);">Sem movimentos.</td></tr>';
    const box = document.getElementById('estoque-lista');
    box.innerHTML = `
      <div class="estoque-hist-topo">
        <button class="btn btn-ghost btn-sm" onclick="carregarEstoque()">← Voltar ao estoque</button>
        <span class="estoque-hist-titulo">Histórico — ${esc(codigo)}</span>
      </div>
      <div class="estoque-hist-scroll">
        <table class="estoque-hist-tabela">
          <thead><tr>
            <th>Tipo</th><th style="text-align:right;">Qtd</th><th style="text-align:right;">Saldo</th>
            <th style="text-align:right;">Custo un.</th><th>Origem / destino</th><th>Quem</th><th>Quando</th><th>Obs</th>
          </tr></thead>
          <tbody>${corpo}</tbody>
        </table>
      </div>`;
    document.getElementById('estoque-resumo').innerHTML = '';
  } catch (e) { toast(e.message, 'error'); }
}

function fecharModais() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
  // Fechar por fora (clique no fundo / Esc) também precisa soltar a câmera do
  // bipar — senão a luz da câmera fica acesa com o modal já fechado.
  if (typeof _pararCameraBipar === 'function') _pararCameraBipar();
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => { if (e.target === overlay) fecharModais(); });
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharModais(); });

function selecionarDia(el, dia) {
  document.querySelectorAll('.dia-pill').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('nova-dia').value = dia;
}

function formatarCEP(input) {
  let v = input.value.replace(/\D/g, '').slice(0, 8);
  if (v.length > 5) v = v.slice(0, 5) + '-' + v.slice(5);
  input.value = v;
}

// (11) 99999-9999 pra celular, (11) 9999-9999 pra fixo — decide pelo
// tamanho enquanto a pessoa digita, sem exigir escolher o formato antes.
function formatarTelefone(input) {
  let v = input.value.replace(/\D/g, '').slice(0, 11);
  if (v.length > 10) v = `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7)}`;
  else if (v.length > 6) v = `(${v.slice(0, 2)}) ${v.slice(2, 6)}-${v.slice(6)}`;
  else if (v.length > 2) v = `(${v.slice(0, 2)}) ${v.slice(2)}`;
  input.value = v;
}

function formatCEP(cep) {
  if (!cep) return '—';
  const c = String(cep).replace(/\D/g, '');
  return c.length === 8 ? c.slice(0, 5) + '-' + c.slice(5) : String(cep);
}

function formatarData(d) {
  if (!d) return '';
  const partes = String(d).split('-');
  if (partes.length !== 3) return String(d);
  const [y, m, day] = partes;
  return `${day}/${m}/${y}`;
}

function formatarDataHora(dt) {
  const d = parseDataBanco(dt);
  if (!d) return '—';
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}

function formatarTempo(minutos) {
  if (minutos < 60) return `${minutos}min`;
  const h = Math.floor(minutos / 60), m = minutos % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = { success: icone('check', 'icone-13'), error: icone('x', 'icone-13'), info: icone('info', 'icone-13') };
  const cor = type === 'success' ? 'var(--success-text)'
            : type === 'error'   ? 'var(--danger-text)'
            : 'var(--accent-text)';

  el.innerHTML = `<span style="display:inline-flex;color:${cor};">${icons[type] || icone('info', 'icone-13')}</span> ${esc(msg)}`;
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}
// ═══ Atendimentos: o que o técnico registrou em campo ══════════════════
//
// Junta num lugar só o que antes ficava espalhado ponto a ponto dentro de
// cada rota. A ordem dos indicadores não é alfabética nem por tamanho: começa
// por "precisa de peça" porque é o único que gera trabalho para alguém —
// atendimento que só termina depois que a peça for comprada.
// `rotulo` conta os do indicador (plural, "2 precisam de peça"); `curto`
// nomeia UM atendimento na linha (singular). Usar o mesmo texto nos dois
// lugares fazia a linha do cliente dizer "PRECISAM DE PEÇA", no plural,
// falando de um só.
const AT_TIPOS = [
  { tipo: 'precisa_peca', rotulo: 'Precisam de peça', curto: 'Precisa de peça',
    classe: 'at-peca',  nota: 'esperando compra' },
  { tipo: 'cotacao_peca', rotulo: 'Cotação de peça',  curto: 'Cotação de peça',
    classe: 'at-cotacao', nota: 'aguardando preço' },
  { tipo: 'volto_depois', rotulo: 'Voltar depois',    curto: 'Volta depois',
    classe: 'at-volta', nota: 'precisa de retorno' },
  { tipo: 'nao_atendido', rotulo: 'Reagendar',        curto: 'Reagendar',
    classe: 'at-nao',   nota: 'visita perdida, remarcar' },
  { tipo: 'resolvido',    rotulo: 'Resolvidos',       curto: 'Resolvido',
    classe: 'at-ok',    nota: 'fechados na hora' },
];

let _atDias = 30;
let _atTipo = '';

function mudarPeriodoDesfechos(dias) {
  _atDias = dias;
  document.querySelectorAll('.at-per').forEach(b =>
    b.classList.toggle('ativo', Number(b.dataset.dias) === dias));
  carregarDesfechos();
}

function filtrarDesfecho(tipo) {
  // Clicar no indicador já ativo desliga o filtro: é o gesto que a pessoa
  // tenta naturalmente para "ver tudo de novo".
  _atTipo = (_atTipo === tipo) ? '' : tipo;
  carregarDesfechos();
}

async function carregarDesfechos() {
  const alvo = document.getElementById('at-conteudo');
  if (!alvo) return;
  alvo.innerHTML = `<div class="loading-row" style="justify-content:center;padding:30px;">
      <div class="spinner"></div> Carregando atendimentos...</div>`;

  let r;
  try {
    r = await api(`/desfechos?dias=${_atDias}${_atTipo ? '&tipo=' + _atTipo : ''}`);
  } catch (e) {
    alvo.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
    return;
  }

  const cartoes = AT_TIPOS.map(t => `
    <button class="at-cartao ${t.classe} ${_atTipo === t.tipo ? 'ativo' : ''}"
            onclick="filtrarDesfecho('${t.tipo}')"
            title="${_atTipo === t.tipo ? 'Clique para ver todos' : 'Clique para ver só estes'}">
      <span class="at-num">${r.contagem[t.tipo] ?? 0}</span>
      <span class="at-rot">${t.rotulo}</span>
      <span class="at-nota">${t.nota}</span>
    </button>`).join('');

  if (!r.atendimentos.length) {
    alvo.innerHTML = `<div class="at-cartoes">${cartoes}</div>
      <div class="historico-vazio">${icone('check', 'icone-24')}
        <p>${_atTipo ? 'Nenhum atendimento desse tipo no período.'
                     : 'Nenhum atendimento registrado neste período.'}</p></div>`;
    return;
  }

  const linhas = r.atendimentos.map(a => {
    const t = AT_TIPOS.find(x => x.tipo === a.desfecho) || {};
    const detalhe = a.peca || a.motivo || '';
    const aparelho = [a.tipo_aparelho, a.modelo].filter(Boolean).join(' · ');
    return `
      <div class="at-linha ${t.classe}${a.pedido_em ? ' pedida' : ''}" id="at-linha-${a.servico_id}">
        <div class="at-quando">
          <span class="at-data">${esc((a.registrado_em || '').slice(0, 10).split('-').reverse().join('/'))}</span>
          <span class="at-hora">${esc((a.registrado_em || '').slice(11, 16))}</span>
        </div>
        <div class="at-quem">
          <div class="at-cliente">${esc(a.cliente) || 'Cliente sem nome'}</div>
          <div class="at-sub">${esc(a.endereco_completo) || ''}</div>
          ${aparelho ? `<div class="at-sub">${esc(aparelho)}</div>` : ''}
        </div>
        <div class="at-oque">
          <span class="at-etiqueta ${t.classe}">${esc(t.curto || a.desfecho)}</span>
          ${detalhe ? `<div class="at-detalhe">${esc(detalhe)}</div>` : ''}
          ${a.observacao ? `<div class="at-obs">${esc(a.observacao)}</div>` : ''}
        </div>
        <div class="at-tecnico">
          ${a.tecnico ? `<span class="at-ponto-cor" style="background:${escCor(a.tecnico_cor)}"></span>${esc(a.tecnico)}` : '—'}
          ${a.numero_os ? `<div class="at-sub">OS ${esc(a.numero_os)}</div>` : ''}
        </div>
        <div class="at-foto" id="at-foto-${a.servico_id}">
          ${a.fotos ? `<button class="at-ver-foto" onclick="verFotosDoAtendimento(${a.servico_id})">
              ${a.fotos} foto${a.fotos !== 1 ? 's' : ''}</button>` : ''}
        </div>
        <div class="at-baixa" id="at-baixa-${a.servico_id}">
          ${a.desfecho === 'precisa_peca' ? botaoBaixa(a) : ''}
        </div>
        ${alertaNoCarro(a)}
      </div>`;
  }).join('');

  alvo.innerHTML = `
    <div class="at-cartoes">${cartoes}</div>
    ${_atTipo ? `<div class="at-filtro-aviso">Mostrando só
        <b>${esc((AT_TIPOS.find(x => x.tipo === _atTipo) || {}).rotulo || '')}</b>
        · <button class="at-limpar" onclick="filtrarDesfecho('${_atTipo}')">ver todos</button></div>` : ''}
    <div class="at-tabela">
      <div class="at-cabecalho">
        <span>Quando</span><span>Cliente</span><span>O que aconteceu</span>
        <span>Técnico</span><span>Etiqueta</span><span>Pedido</span>
      </div>
      ${linhas}
    </div>`;

  // Depois do render: o innerHTML acima substitui todo o conteúdo do painel
  // e apagaria o aviso se ele fosse inserido antes.
  avisarPecasNoCarro(r.atendimentos);
}

// Busca a foto só quando alguém pede. Trazer as imagens junto da lista
// deixaria a abertura da aba lenta por um dado que se olha de um por vez.
async function verFotosDoAtendimento(servicoId) {
  const slot = document.getElementById(`at-foto-${servicoId}`);
  if (!slot) return;
  slot.innerHTML = '<span class="at-sub">abrindo...</span>';
  try {
    const r = await api(`/servicos/${servicoId}/fotos`);
    if (!(r.fotos || []).length) { slot.innerHTML = '<span class="at-sub">sem foto</span>'; return; }
    slot.innerHTML = r.fotos.map(f =>
      `<img class="at-thumb" src="${f.foto}" alt="Etiqueta"
            title="${esc(f.criado_em || '')}" onclick="ampliarFoto(this.src)">`).join('');
    ampliarFoto(r.fotos[0].foto);   // já abre a primeira: foi o que a pessoa pediu
  } catch (e) {
    slot.innerHTML = `<span class="at-sub">${esc(e.message)}</span>`;
  }
}


// ─── Baixa da peça ──────────────────────────────────────────────────
//
// "Já pedi" fecha o circuito: marca aqui E escreve na planilha qual peça foi
// pedida para qual cliente. Antes, entre o técnico dizer "precisa de peça" e
// a compra chegar, o pedido existia só na memória de quem comprou — e
// ninguém conseguia responder "essa peça já foi pedida?".
//
// A linha inteira fica verde, e não só o botão: com vinte linhas na tela, é a
// cor da linha que responde a pergunta de longe.
function botaoBaixa(a) {
  if (a.pedido_em) {
    const quando = (a.pedido_em || '').slice(0, 10).split('-').reverse().join('/');
    return `<span class="at-pedida" title="Pedida em ${esc(a.pedido_em)}${
      a.pedido_por ? ' por ' + esc(a.pedido_por) : ''}">✓ pedida ${esc(quando)}</span>`;
  }
  return `<button class="at-btn-baixa" onclick="darBaixaPeca(${a.servico_id})">
            Já pedi</button>`;
}

async function darBaixaPeca(servicoId) {
  const slot = document.getElementById(`at-baixa-${servicoId}`);
  if (!slot) return;
  const original = slot.innerHTML;
  slot.innerHTML = '<span class="at-sub">gravando...</span>';
  try {
    const r = await api(`/desfechos/${servicoId}/pedido`, { method: 'POST' });
    document.getElementById(`at-linha-${servicoId}`)?.classList.add('pedida');
    slot.innerHTML = botaoBaixa({ pedido_em: r.pedido_em, pedido_por: r.pedido_por });
    // O aviso aparece quando a baixa foi gravada mas a planilha falhou. É
    // importante distinguir: a baixa VALEU, só a linha da planilha não saiu.
    toast(r.aviso || 'Peça marcada como pedida e registrada na planilha',
          r.aviso ? 'error' : 'success');
  } catch (e) {
    slot.innerHTML = original;
    toast(e.message, 'error');
  }
}


// ─── "Essa peça é de quem?" respondido pelo próprio sistema ────────────
//
// O técnico registrou em campo que precisava da peça X para o cliente Y.
// Quando a compra dessa peça chega da Panasonic, o servidor casa pelo CÓDIGO
// e a tela mostra de quem é — em vez de alguém ter que lembrar.
//
// SUGERE, não preenche sozinho. Duas pessoas podem precisar da mesma peça na
// mesma semana; e este projeto já teve erro real de casamento automático de
// cliente (ver services/agoraos.py), que escreveu na OS de outra pessoa sem
// possibilidade de desfazer. Um clique é barato; nome errado numa peça, não.
function sugestaoDeCliente(p) {
  const lista = p.sugestao_cliente || [];
  if (!lista.length || p.cliente_final) return '';

  if (lista.length === 1) {
    const s = lista[0];
    return `
      <div class="peca-sugere">
        <span class="peca-sugere-txt">
          O técnico pediu esta peça para <b>${esc(s.cliente)}</b>
          ${s.aparelho ? `· ${esc(s.aparelho)}` : ''}
          ${s.numero_os ? `· OS ${esc(s.numero_os)}` : ''}
          ${s.ja_pedida ? '<span class="peca-sugere-ok">já dada baixa</span>' : ''}
        </span>
        <button class="peca-sugere-btn"
                onclick="aplicarSugestaoCliente(${p.linha}, ${argJs(s.cliente)})">
          usar este cliente</button>
      </div>`;
  }

  // Mais de um candidato: mostra todos e deixa a escolha com quem sabe.
  return `
    <div class="peca-sugere ambigua">
      <span class="peca-sugere-txt">
        <b>${lista.length} clientes</b> pediram esta peça — escolha qual:
      </span>
      <span class="peca-sugere-opcoes">
        ${lista.map(s => `
          <button class="peca-sugere-btn"
                  onclick="aplicarSugestaoCliente(${p.linha}, ${argJs(s.cliente)})">
            ${esc(s.cliente)}${s.numero_os ? ' · OS ' + esc(s.numero_os) : ''}</button>`).join('')}
      </span>
    </div>`;
}

function aplicarSugestaoCliente(linha, cliente) {
  const campo = document.getElementById(`peca-cliente-${linha}`);
  if (!campo) return;
  campo.value = cliente;
  // Dispara a mesma gravação do preenchimento manual — um caminho só de
  // escrita, para os dois não divergirem.
  salvarPecaInline(linha);
}


// ═══ Estoque do carro do técnico ══════════════════════════════════════
//
// O técnico carrega um jogo de peças de giro na van, e isso só existia na
// cabeça dele. Sem esta lista, o escritório compra peça que já está rodando
// na rua e o cliente espera a compra chegar enquanto a peça passa na porta.
let _carroTecnicoId = null;

async function abrirCarro(tecnicoId, nome) {
  _carroTecnicoId = tecnicoId;
  const modal = document.getElementById('modal-carro');
  modal.querySelector('.carro-titulo').textContent = `Peças no carro · ${nome}`;
  modal.classList.add('open');
  await recarregarCarro();
  setTimeout(() => document.getElementById('carro-codigo')?.focus(), 80);
}

function fecharCarro() {
  document.getElementById('modal-carro')?.classList.remove('open');
  _carroTecnicoId = null;
}

async function recarregarCarro() {
  const lista = document.getElementById('carro-lista');
  lista.innerHTML = '<div class="loading-row" style="padding:16px;">Carregando...</div>';
  try {
    const r = await api(`/tecnicos/${_carroTecnicoId}/carro`);
    if (!(r.pecas || []).length) {
      lista.innerHTML = `<div class="carro-vazio">Nenhuma peça registrada no carro deste técnico.</div>`;
      return;
    }
    lista.innerHTML = r.pecas.map(pc => `
      <div class="carro-item">
        <div class="carro-info">
          <div class="carro-codigo">${esc(pc.codigo)}</div>
          ${pc.descricao ? `<div class="carro-desc">${esc(pc.descricao)}</div>` : ''}
        </div>
        <div class="carro-qtd">
          <button class="carro-btn" onclick="mudarQtdCarro(${pc.id}, ${pc.quantidade - 1})"
                  title="Tirar uma">−</button>
          <span class="carro-num">${pc.quantidade}</span>
          <button class="carro-btn" onclick="mudarQtdCarro(${pc.id}, ${pc.quantidade + 1})"
                  title="Somar uma">+</button>
        </div>
      </div>`).join('');
  } catch (e) {
    lista.innerHTML = `<div class="vcep-erro" style="margin:0;">${esc(e.message)}</div>`;
  }
}

async function mudarQtdCarro(pecaId, quantidade) {
  try {
    await api(`/tecnicos/carro/${pecaId}`, {
      method: 'PUT', body: JSON.stringify({ quantidade }),
    });
    await recarregarCarro();
  } catch (e) { toast(e.message, 'error'); }
}

async function adicionarPecaCarro() {
  const codigo = document.getElementById('carro-codigo').value.trim();
  const descricao = document.getElementById('carro-desc').value.trim();
  const quantidade = Number(document.getElementById('carro-qtd').value) || 1;
  if (!codigo) { toast('Informe o código da peça', 'error'); return; }
  try {
    await api(`/tecnicos/${_carroTecnicoId}/carro`, {
      method: 'POST', body: JSON.stringify({ codigo, descricao, quantidade }),
    });
    document.getElementById('carro-codigo').value = '';
    document.getElementById('carro-desc').value = '';
    document.getElementById('carro-qtd').value = 1;
    document.getElementById('carro-codigo').focus();
    await recarregarCarro();
  } catch (e) { toast(e.message, 'error'); }
}


// ─── "Essa peça já está num carro" ────────────────────────────────────
//
// Aparece ANTES do botão de comprar, de propósito: é a pergunta que precisa
// ser feita antes de gastar. Sem isso, o escritório pede peça que já está
// rodando na van e o cliente espera a entrega enquanto a peça passa na porta
// dele.
function alertaNoCarro(a) {
  const lista = a.no_carro || [];
  if (!lista.length) return '';
  const quem = lista.map(c =>
    `<b>${esc(c.tecnico)}</b>${c.quantidade > 1 ? ` (${c.quantidade})` : ''}`).join(', ');
  return `<div class="at-no-carro">
      <span class="at-carro-icone" aria-hidden="true">🚗</span>
      Já está no carro de ${quem} — confira antes de comprar
    </div>`;
}

// Aviso de uma vez só ao abrir a aba. Uma faixa por linha se perde na
// rolagem; este resume no topo e some quando o usuário fecha.
function avisarPecasNoCarro(atendimentos) {
  const comCarro = (atendimentos || []).filter(a => (a.no_carro || []).length);
  if (!comCarro.length) return;
  if (document.getElementById('aviso-carro')) return;

  // ENTRA NO FLUXO, no topo do painel — não flutua sobre a lista.
  // Fixo no rodapé, ele cobria a linha que estivesse embaixo enquanto a
  // pessoa rolava; no celular isso era metade da tela tapada. No topo ele
  // é visto de imediato e não esconde nada.
  const alvo = document.getElementById('at-conteudo');
  if (!alvo) return;

  const aviso = document.createElement('div');
  aviso.id = 'aviso-carro';
  aviso.className = 'aviso-carro';
  aviso.setAttribute('role', 'status');
  aviso.innerHTML = `
    <span class="aviso-carro-icone" aria-hidden="true">🚗</span>
    <span><b>${comCarro.length} peça${comCarro.length !== 1 ? 's' : ''}</b>
      que ${comCarro.length !== 1 ? 'os técnicos pediram já estão' : 'o técnico pediu já está'}
      no carro de alguém. Confira antes de comprar.</span>
    <button class="aviso-carro-fechar" onclick="this.parentElement.remove()"
            aria-label="Fechar">&times;</button>`;
  alvo.prepend(aviso);
}
