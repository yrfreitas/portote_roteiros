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
const VERSAO_PAINEL = 'v34';

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

  const ocupado = document.querySelector('.modal-overlay.open')
    || (document.activeElement
        && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName));
  if (ocupado) return;

  toast('Atualizando o sistema...', 'info');
  setTimeout(() => location.reload(), 700);
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

  // Mudou, mas o usuário está no meio de alguma coisa. Não gravamos a revisão
  // nova: assim a checagem seguinte torna a detectar a diferença e aplica
  // quando der. Perder a atualização por causa de um campo focado seria pior
  // que atrasá-la.
  if (!_telaOciosa()) return;

  _revisaoConhecida = revisao;
  await recarregarViewAtual();
  toast('Dados atualizados', 'info');
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
  carregarTecnicos();
  _vcepRenderHistorico();
  carregarSeloPecas();
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
function switchMainTab(tab) {
  const isRoteiros  = tab === 'roteiros';
  const isCep       = tab === 'cep';
  const isHistorico = tab === 'historico';
  const isPecas     = tab === 'pecas';
  const isDiag      = tab === 'diagnostico';

  document.getElementById('panel-roteiros-sidebar').style.display = isRoteiros ? 'flex' : 'none';
  document.getElementById('panel-roteiros-main').style.display = isRoteiros ? 'block' : 'none';
  document.getElementById('panel-cep').style.display = isCep ? 'block' : 'none';
  document.getElementById('panel-historico').style.display = isHistorico ? 'block' : 'none';
  document.getElementById('panel-pecas').style.display = isPecas ? 'block' : 'none';
  document.getElementById('panel-diagnostico').style.display = isDiag ? 'block' : 'none';

  document.getElementById('mtab-roteiros').classList.toggle('active', isRoteiros);
  document.getElementById('mtab-cep').classList.toggle('active', isCep);
  document.getElementById('mtab-historico').classList.toggle('active', isHistorico);
  document.getElementById('mtab-pecas').classList.toggle('active', isPecas);
  document.getElementById('mtab-diagnostico').classList.toggle('active', isDiag);

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
  corpo.innerHTML = `<div class="loading-row" style="display:flex;justify-content:center;gap:10px;padding:20px;"><div class="spinner"></div> Procurando pontos sem setor...</div>`;
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
    corpo.innerHTML = `<div style="padding:18px;text-align:center;color:var(--text-muted);font-size:12px;">Nenhum ponto sem setor. Tudo classificado.</div>`;
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
  if (ids.length === 0) { toast('Marque ao menos um ponto.', 'error'); return; }

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

  // ── Higiene dos dados
  partes.push(`<div class="diag-secao">Dados</div>`);
  const semSetor = (d.setores && d.setores.sem_setor) || 0;
  partes.push(_linhaDiag('Pontos sem setor',
    semSetor === 0 ? 'ok' : 'aviso',
    semSetor === 0 ? 'todos classificados' : `${semSetor} sem classificação`,
    semSetor ? `<button class="btn btn-primary btn-sm" onclick="abrirClassificacaoEmLote()">Classificar agora</button>` : ''));

  partes.push(_linhaDiag('Chave de sessão',
    d.secret_fixa ? 'ok' : 'ruim',
    d.secret_fixa ? 'fixa (sessão sobrevive a atualização)' : 'temporária — todo deploy desloga',
    d.secret_fixa ? '' : 'Defina SECRET_KEY nas variáveis do Railway.'));

  // ── Erros de navegador
  const er = d.erros || {};
  partes.push(`<div class="diag-secao">Erros na tela (últimos)</div>`);
  if (!er.total) {
    partes.push(_linhaDiag('Nenhum erro registrado', 'ok', 'limpo'));
  } else {
    partes.push((er.ultimos || []).map(e => `
      <div class="diag-erro">
        <div class="diag-erro-msg">${esc(e.mensagem)}</div>
        <div class="diag-detalhe">${esc(e.quando)} · ${esc(e.origem)} · ${esc(e.versao)} · ${esc(e.url)}</div>
      </div>`).join(''));
  }

  alvo.innerHTML = `<div class="diag-versao">Sistema na versão ${esc(d.app || '—')}</div>` + partes.join('');
}


// ─── Aviso de pontos sem setor ──────────────────────────────────────
// O relatório por setor é o número que serve para cobrar a fabricante. Com
// 60% dos pontos sem classificação ele não vale nada — e ninguém classifica
// o que não aparece na frente.
async function verificarPontosSemSetor() {
  let d;
  try { d = await api('/setores/resumo'); } catch { return; }

  const total = d.sem_setor || 0;
  let faixa = document.getElementById('aviso-sem-setor');

  if (!total) { if (faixa) faixa.remove(); return; }

  if (!faixa) {
    faixa = document.createElement('div');
    faixa.id = 'aviso-sem-setor';
    faixa.className = 'aviso-sem-setor';
    const main = document.getElementById('panel-roteiros-main');
    if (main) main.prepend(faixa); else return;
  }

  faixa.innerHTML = `
    <span><b>${total}</b> ponto${total !== 1 ? 's' : ''} sem setor —
      o relatório por frente fica incompleto enquanto isso.</span>
    <button class="btn btn-primary btn-sm" onclick="abrirClassificacaoEmLote()">Classificar</button>`;
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
            <div><b>${t.pontos}</b><span>pontos</span></div>
            <div><b>${t.pendentes}</b><span>a fazer</span></div>
            <div><b>${t.km}</b><span>km</span></div>
            <div><b>${t.km_por_ponto}</b><span>km/ponto</span></div>
            <div><b>${t.taxa_conclusao}%</b><span>concluído</span></div>
            <div><b>${t.rotas}</b><span>rotas</span></div>
          </div>
          <div class="comp-barra"><span style="width:${Math.min(100, t.fatia)}%;background:${escCor(t.cor)}"></span></div>
        </div>`).join('')}
    </div>
    <div class="diag-detalhe" style="margin-top:8px;">
      <b>km/ponto</b> é o número que compara de verdade: quilometragem alta com
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

function avatarTecnico(t) {
  const inicial = (t.nome || '?').trim().charAt(0).toUpperCase();
  return t.foto
    ? `<img src="${t.foto}" class="tec-avatar" alt="" onclick="escolherFotoTecnico(${t.id})" title="Trocar foto">`
    : `<div class="tec-avatar sem-foto" style="background:${escCor(t.cor)}"
         onclick="escolherFotoTecnico(${t.id})" title="Adicionar foto">${esc(inicial)}</div>`;
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
          <div class="tecnico-nome" style="color:${escCor(t.cor)}">${esc(t.nome)}</div>
          <span class="tec-contagem" id="tec-contagem-${t.id}"></span>
          <div class="tecnico-actions" onclick="event.stopPropagation()">
            <button class="btn-add-ficha" onclick="abrirModalNovaFicha(${t.id})" title="Nova ficha">+ Ficha</button>
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
      <div class="ficha-item ${ativa ? 'active' : ''} ${concluida ? 'ficha-item-concluida' : ''}"
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
          <span class="badge ${f.total_servicos > 0 ? 'accent' : ''}">${f.total_servicos} ponto${f.total_servicos !== 1 ? 's' : ''}</span>
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
             title="Clique para classificar estes pontos">
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
        <div class="vg-label">Ponto${totalPontos !== 1 ? 's' : ''} Atendido${totalPontos !== 1 ? 's' : ''}</div>
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
            <span>${f.total_servicos} ponto${f.total_servicos !== 1 ? 's' : ''}</span>
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

  lista.innerHTML = `
    <div class="pecas-barra">
      <span class="pecas-contagem">${pedidos.length} compra${pedidos.length !== 1 ? 's' : ''}</span>
      ${r.sugestao_peca_ativa
        ? `<span class="conc-tag ok" title="As peças vêm do XML da nota fiscal enviada pela Panasonic">peça automática ligada</span>`
        : `<span class="conc-tag neutro" title="Configure IMAP_USER e IMAP_PASSWORD para ler as notas fiscais">peça automática desligada</span>`}
      <button class="btn btn-ghost btn-sm" onclick="revisarAmarelas()">Revisar amarelas</button>
      <button class="btn btn-primary btn-sm" style="margin-left:auto;" onclick="salvarPecasEmLote()">
        Vincular todas preenchidas
      </button>
    </div>
    <div id="pecas-revisao"></div>
  ` + pedidos.map(p => `
    <div class="peca-card" id="peca-${p.linha}" data-linha="${p.linha}">
      <div class="peca-topo">
        <div>
          <div class="peca-valor">${esc(p.valor) || '—'}</div>
          <div class="peca-meta">NF ${esc((p.nota_fiscal || '').slice(-8))} · ${esc(p.data)}</div>
        </div>
        ${p.cliente_final
          ? `<span class="conc-tag ok">${esc(p.cliente_final)}</span>`
          : `<span class="conc-tag neutro">sem cliente</span>`}
      </div>

      <div class="peca-sugestao-slot" id="sugestao-${p.linha}"
           data-nota="${esc(p.nota_fiscal)}"></div>

      <div class="peca-form">
        <div class="form-group" style="margin:0;">
          <label class="form-label">Cliente</label>
          <input class="form-input" list="lista-clientes" id="peca-cliente-${p.linha}"
                 value="${esc(p.cliente_final)}" placeholder="Escolha ou digite...">
        </div>
        <div class="form-group" style="margin:0;">
          <label class="form-label">Peça / Modelo</label>
          <input class="form-input" id="peca-desc-${p.linha}"
                 value="${esc(p.peca)}" placeholder="Ex: NR-BB64PV1BA">
        </div>
      </div>

      <button class="btn btn-primary btn-sm" style="margin-top:10px;"
              onclick="salvarPeca(${p.linha})">Vincular</button>
    </div>
  `).join('') + `
    <datalist id="lista-clientes">
      ${clientesConhecidos.map(c => `<option value="${esc(c.nome)}">${esc(c.aparelho)}${c.modelo ? ' · ' + esc(c.modelo) : ''}</option>`).join('')}
    </datalist>`;

  atualizarSeloPecas(r.pendentes ?? pedidos.filter(p => !p.cliente_final).length);

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

function usarSugestao(linha, botao) {
  const campo = document.getElementById(`peca-desc-${linha}`);
  const sugestao = campo?.dataset.sugestao || '';
  if (campo && sugestao) {
    campo.value = sugestao;
    botao.textContent = 'Aplicado';
    botao.disabled = true;
  }
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

async function salvarPecasEmLote() {
  const cards = Array.from(document.querySelectorAll('.peca-card'));
  const itens = cards.map(c => {
    const linha = parseInt(c.dataset.linha, 10);
    return {
      linha,
      cliente: document.getElementById(`peca-cliente-${linha}`)?.value.trim() || '',
      peca: document.getElementById(`peca-desc-${linha}`)?.value.trim() || '',
    };
  }).filter(i => i.cliente);

  if (itens.length === 0) {
    toast('Preencha o cliente de pelo menos uma peça', 'error');
    return;
  }
  if (!confirm(`Vincular ${itens.length} peça(s) de uma vez?`)) return;

  try {
    const r = await api('/pedidos/lote', {
      method: 'PUT',
      body: JSON.stringify({ itens }),
    });
    toast(r.mensagem, (r.falhas || []).length ? 'error' : 'success');
    (r.falhas || []).forEach(f => toast(`Linha ${f.linha}: ${f.erro}`, 'error'));
    // Em lote não abre modal por linha — seriam N interrupções seguidas. As
    // duvidosas viram aviso e ficam pra resolver uma a uma pelo vínculo normal.
    (r.revisar_agoraos || []).forEach(x =>
      toast(`Linha ${x.linha} não foi pro AgoraOS: ${x.motivo}`, 'error'));
    await carregarPecas();
  } catch (e) { toast(e.message, 'error'); }
}

async function salvarPeca(linha) {
  const cliente = document.getElementById(`peca-cliente-${linha}`).value.trim();
  const peca = document.getElementById(`peca-desc-${linha}`).value.trim();

  if (!cliente) { toast('Escolha ou digite o cliente', 'error'); return; }

  const card = document.getElementById(`peca-${linha}`);
  const btn = card.querySelector('button');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Gravando...';

  try {
    const r = await api(`/pedidos/${linha}`, {
      method: 'PUT',
      body: JSON.stringify({ cliente, peca }),
    });
    toast(`Peça vinculada a ${cliente}`, 'success');
    // A resposta do AgoraOS é lida ANTES do reload: carregarPecas() tira o
    // card da lista (a peça deixou de estar pendente) e levaria a prévia junto.
    const ag = r.agoraos;
    await carregarPecas();
    tratarRetornoAgoraOS(linha, cliente, peca, ag);
  } catch (e) {
    toast(e.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Vincular';
  }
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
  if (!confirm('Remover este técnico e todas as suas fichas?')) return;

  try {
    await api(`/tecnicos/${id}`, { method: 'DELETE' });
    if (fichaAtiva?.tecnico_id === id) mostrarEstadoVazio();
    await carregarTecnicos();
    toast('Técnico removido', 'info');
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
  const detail = document.getElementById('ficha-detail');
  detail.innerHTML = `<div class="loading-row" style="height:200px;display:flex;align-items:center;justify-content:center;gap:10px;"><div class="spinner"></div><span style="color:var(--text-muted);">Carregando roteiro...</span></div>`;

  if (mapaLeaflet) { mapaLeaflet.remove(); mapaLeaflet = null; }

  let ficha, servicos, resumo;
  try {
    ({ ficha, servicos, resumo } = await api(`/fichas/${id}`));
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
        <button class="btn btn-primary" onclick="abrirModalAddServico(${ficha.id})">+ Adicionar Ponto</button>
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

    ${semCoord > 0 ? `<div class="vcep-aviso" style="margin-bottom:18px;">${semCoord} ponto${semCoord > 1 ? 's' : ''} sem coordenada — não entra${semCoord > 1 ? 'm' : ''} no cálculo da rota. Remova e cadastre de novo para corrigir.</div>` : ''}

    <div class="stats-strip">
      <div class="stat-card"><div class="stat-label">Pontos de Serviço</div><div class="stat-value" style="color:${cor}"><span class="stat-num" id="stat-num-pontos">0</span><span class="stat-unit">pts</span></div></div>
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
                ? `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:14px;">Nearest Neighbor + refinamento <strong>2-opt</strong>, recalculado ao adicionar ou remover pontos.<br><br><span style="color:var(--text-muted);font-size:11px;display:inline-flex;align-items:center;gap:4px;">${icone('info', 'icone-11')} Distância por ruas (linha reta × 1.4) · 40 km/h médios · 20 min por parada</span></div>
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
            ${temCoordenadas ? `<span class="badge accent" style="margin-left:auto;">${servicos.length} ponto${servicos.length !== 1 ? 's' : ''}</span>` : ''}
          </div>
          <div id="mapa-roteiro" class="mapa-container">
            ${!temCoordenadas ? `<div class="mapa-empty"><div style="margin-bottom:8px;">${icone('pin', 'icone-28')}</div><div style="font-size:12px;color:var(--text-muted);">Adicione pontos com<br>coordenadas para ver o mapa</div></div>` : ''}
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
    return `<div class="loading-row" style="padding:40px;text-align:center;"><div style="margin-bottom:8px;">${icone('pin', 'icone-24')}</div><div>Nenhum ponto adicionado ainda.</div><div style="font-size:11px;margin-top:4px;color:var(--text-muted);">Clique em "+ Adicionar Ponto" para montar o roteiro.</div></div>`;
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
        <button class="step-num step-num-btn" style="background:${cor}20;border-color:${cor}60;color:${cor}"
                onclick="alternarStatusServico(${s.id},'${feito ? 'pendente' : 'concluido'}',${ficha.id})"
                title="${feito ? 'Marcar como pendente' : 'Marcar como concluído'}">
          ${feito ? icone('check', 'icone-13') : i + 1}
        </button>
        <div class="roteiro-info">
          <div class="roteiro-cep" style="color:${cor}">${esc(formatCEP(s.cep))}</div>
          <div class="roteiro-endereco">${s.numero ? `<strong>Nº ${esc(s.numero)}</strong> · ` : ''}${esc(s.endereco_completo) || '—'}</div>
          ${s.cliente ? `<div class="roteiro-cliente">${icone('usuario', 'icone-11')} ${esc(s.cliente)}${s.descricao ? ' · ' + esc(s.descricao) : ''}</div>` : ''}
          ${aparelho ? `<div class="roteiro-aparelho">${icone('ferramenta', 'icone-11')} ${esc(aparelho)}</div>` : ''}
          ${(() => {
            const st = setorPorId(s.setor_id);
            const os = s.numero_os ? `<span class="roteiro-os">OS ${esc(s.numero_os)}</span>` : '';
            const marca = st
              ? `<span class="roteiro-setor" style="color:${escCor(st.cor)};border-color:${escCor(st.cor)}55;background:${escCor(st.cor)}18;">${esc(st.nome)}</span>`
              : '';
            return (os || marca) ? `<div class="roteiro-etiquetas">${marca}${os}</div>` : '';
          })()}
          ${(!s.lat || !s.lng) ? `<div class="roteiro-cliente" style="color:var(--danger-text);display:flex;align-items:center;gap:4px;">${icone('alerta', 'icone-11')} sem coordenada — fora do cálculo</div>` : ''}
        </div>
        <div class="roteiro-actions">
          ${(s.lat && s.lng) ? `<a href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lng}&zoom=16" target="_blank" rel="noopener" title="Ver no mapa" style="color:${cor};padding:4px 8px;display:inline-flex;">${icone('externo', 'icone-13')}</a>` : ''}
          ${(s.lat && s.lng) ? `<a href="https://waze.com/ul?ll=${s.lat},${s.lng}&navigate=yes" target="_blank" rel="noopener" title="Navegar com Waze" style="color:${cor};padding:4px 8px;display:inline-flex;">${icone('navegacao', 'icone-13')}</a>` : ''}
          <button class="btn-a-caminho" onclick="avisarACaminho(${s.id})" title="Avisar no WhatsApp que está a caminho deste cliente">A caminho</button>
          <button class="btn-editar" onclick="transferirPonto(${s.id}, '${esc(s.cliente || 'este ponto').replace(/'/g, "\'")}')" title="Passar este ponto para outro técnico">${icone('usuario', 'icone-12')}</button>
          <button class="btn-editar" onclick="abrirModalEditarServico(${s.id})" title="Editar ponto">${icone('editar', 'icone-12')}</button>
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
  if (!s) { toast('Ponto não encontrado', 'error'); return; }

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
    toast('Nenhum ponto na rota ainda', 'error');
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

  if (ordenados.length === 0) { toast('Nenhum ponto com endereço válido', 'error'); return; }

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
             desc:'Nenhum ponto marcado — este CEP definiria o trajeto do dia' });
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

  if (d <= 10)      m.push({ tipo:'pos', titulo:'Ponto muito próximo', desc:`${fmtKm(d)} km do ponto mais próximo nessa rota` });
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
  const servem    = [];
  const naoServem = [];
  r.sugestoes.forEach((s, i) => {
    (s.classificacao === 'fora' && !s.vazia ? naoServem : servem).push(monta(s, i));
  });

  // Estado honesto: se nada passou da régua, dizer isso. A tela antiga sempre
  // elegia um vencedor, mesmo quando não havia vencedor — e era isso que
  // levava a botar ponto numa rota que não tinha nada a ver com o endereço.
  const alerta = servem.length === 0 ? `
    <div class="vcep-alerta-nenhuma">
      ${icone('alerta', 'icone-13')}
      <div>
        <strong>Nenhuma rota atual atende bem esse endereço.</strong><br>
        Todas ficam fora de mão. Considere criar um novo dia na aba "Novo dia"
        em vez de forçar o encaixe.
      </div>
    </div>` : '';

  const recolhidas = naoServem.length ? `
    <button type="button" class="vcep-toggle-fora" onclick="vcepAlternarFora(this)">
      Mostrar outras ${naoServem.length} rota${naoServem.length !== 1 ? 's' : ''} — fora de mão
    </button>
    <div class="vcep-fora-lista" style="display:none;">${naoServem.join('')}</div>` : '';

  return `<div class="vcep-analise-wrap">
    <div id="vcep-mapa-encaixe" class="vcep-mapa"></div>
    <div id="vcep-sim-barra" class="vcep-sim-barra">
      <span class="vcep-sim-dica">Clique num dia para ver como a rota ficaria com este endereço.</span>
    </div>
    ${alerta}
    <div class="vcep-analise-label">${servem.length} rota${servem.length !== 1 ? 's' : ''} que ${servem.length !== 1 ? 'servem' : 'serve'}</div>
    ${servem.join('')}
    ${recolhidas}
  </div>`;
}

// ─── Mapa do verificador de encaixe ─────────────────────────────────────
// O número respondia "quanto encaixa". O mapa responde "onde", que é a
// pergunta que a cabeça faz primeiro. Ver o CEP caindo no meio do aglomerado
// de segunda do Pedro decide a questão sem ler nada.
let vcepMapa = null;
let vcepCamadas = [];   // uma camada por sugestão, para o destaque cruzado
let vcepAlvoMarker = null;

function vcepRenderizarMapa(r) {
  try {
    _vcepDesenharMapa(r);
  } catch (e) {
    // O mapa é apoio à decisão, não a decisão. Se ele falhar, a análise em
    // texto — que é a informação essencial — não pode cair junto.
    console.error('Falha ao desenhar o mapa de encaixe:', e);
    const el = document.getElementById('vcep-mapa-encaixe');
    if (el) el.style.display = 'none';
  }
}

function _vcepDesenharMapa(r) {
  const el = document.getElementById('vcep-mapa-encaixe');
  if (!el || !r || typeof L === 'undefined') return;
  if (!Number.isFinite(r.lat) || !Number.isFinite(r.lng)) return;

  // O Leaflet guarda estado no elemento; recriar sem destruir deixa o mapa
  // cinza quando a tela é redesenhada (e ela é, a cada nova consulta).
  if (vcepMapa) { vcepMapa.remove(); vcepMapa = null; }
  vcepCamadas = [];

  // O setView TEM que vir junto com a criação, antes de qualquer camada.
  // Sem visão definida o mapa não tem origem de pixel, e o primeiro
  // circleMarker adicionado estoura com "Cannot read properties of undefined
  // (reading 'intersects')" — o renderizador tenta cruzar os limites da tela
  // com os do desenho, e os da tela ainda não existem.
  vcepMapa = L.map(el, { scrollWheelZoom: false, attributionControl: false })
              .setView([r.lat, r.lng], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(vcepMapa);

  // Coordenada que não seja número finito envenena os limites e faz o
  // fitBounds falhar depois, longe daqui — filtrar na entrada sai mais barato
  // que caçar o efeito lá na frente.
  const valida = (p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng);

  const limites = [[r.lat, r.lng]];

  (r.sugestoes || []).forEach((s, i) => {
    const camada = L.layerGroup().addTo(vcepMapa);
    const cor = s.tecnico_cor || '#4f8dfb';
    // "Fora de mão" entra apagado: continua no mapa para dar noção de onde as
    // outras rotas passam, sem competir com o que de fato interessa.
    const fraca = s.classificacao === 'fora' && !s.vazia;

    (s.pontos || []).filter(valida).forEach(p => {
      L.circleMarker([p.lat, p.lng], {
        radius: fraca ? 3 : 5,
        color: cor, fillColor: cor,
        fillOpacity: fraca ? 0.25 : 0.85,
        weight: fraca ? 1 : 2,
        opacity: fraca ? 0.3 : 0.9,
      }).addTo(camada);
      if (!fraca) limites.push([p.lat, p.lng]);
    });

    // A linha até o ponto mais próximo é o que torna "2,1 km fora da rota"
    // uma distância que se enxerga em vez de um número para acreditar.
    if (valida(s.ponto_proximo) && !fraca) {
      L.polyline([[r.lat, r.lng], [s.ponto_proximo.lat, s.ponto_proximo.lng]], {
        color: cor, weight: 2, opacity: 0.5, dashArray: '4,6',
      }).addTo(camada);
    }

    vcepCamadas[i] = { camada, cor };
  });

  // O alvo vai por último para ficar acima de tudo, e é visualmente diferente
  // dos pontos de rota — é a pergunta, não uma das respostas.
  vcepAlvoMarker = L.circleMarker([r.lat, r.lng], {
    radius: 9, color: '#fff', fillColor: '#e02020', fillOpacity: 1, weight: 3,
  }).addTo(vcepMapa).bindTooltip(
    r.endereco || r.cep || 'Endereço consultado', { direction: 'top' }
  );

  // Só reenquadra se houver mais de um ponto e os limites forem válidos.
  // Com o alvo sozinho, o fitBounds daria zoom máximo num ponto único; o
  // setView de cima já deixou um enquadramento razoável nesse caso.
  if (limites.length > 1) {
    const caixa = L.latLngBounds(limites);
    if (caixa.isValid()) vcepMapa.fitBounds(caixa.pad(0.2));
  }

  // O container nasce com display:none dentro da aba; sem isso o Leaflet
  // calcula tamanho zero e o mapa aparece cortado.
  setTimeout(() => vcepMapa && vcepMapa.invalidateSize(), 120);
}

// Passar o mouse no card acende a rota correspondente no mapa. É o que liga
// as duas metades da tela: sem isso são duas listas que não se conversam.
function vcepDestacarNoMapa(indice) {
  if (!vcepMapa) return;
  vcepCamadas.forEach((c, i) => {
    if (!c) return;
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
let vcepCamadaSimulacao = null;

async function vcepSimularNoMapa(indice) {
  const r = verificacaoAtual;
  if (!r || !vcepMapa) return;
  const s = r.sugestoes?.[indice];
  if (!s) return;

  const barra = document.getElementById('vcep-sim-barra');
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

  // Limpa só a camada da simulação — os pontos de contexto das outras rotas
  // continuam no mapa, senão o usuário perde a noção de onde tudo está.
  if (vcepCamadaSimulacao) { vcepCamadaSimulacao.remove(); vcepCamadaSimulacao = null; }
  vcepCamadaSimulacao = L.layerGroup().addTo(vcepMapa);

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
  if (caixa.isValid()) vcepMapa.fitBounds(caixa.pad(0.15));

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
    // Fechar o card também limpa a simulação: deixar o trajeto desenhado sem
    // nenhum dia selecionado faria o mapa mostrar uma rota que não é resposta
    // a pergunta nenhuma.
    if (vcepCamadaSimulacao) { vcepCamadaSimulacao.remove(); vcepCamadaSimulacao = null; }
    const barra = document.getElementById('vcep-sim-barra');
    if (barra) barra.innerHTML = `<span class="vcep-sim-dica">Clique num dia para ver como a rota ficaria com este endereço.</span>`;
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
    <div class="vcep-motivo vcep-motivo-${m.tipo}">
      <div class="vcep-motivo-icon vcep-motivo-icon-${m.tipo}">${icones[m.tipo]}</div>
      <div>
        <div class="vcep-motivo-titulo">${esc(m.titulo)}</div>
        <div class="vcep-motivo-desc">${esc(m.desc)}</div>
      </div>
    </div>`).join('');

  el.innerHTML = `
    <div class="vcep-detalhe-body">
      <div class="vcep-detalhe-titulo">Por que essa pontuação?</div>
      <div class="vcep-motivos">${motHtml}</div>
      <div class="vcep-metricas">
        <div class="vcep-metrica"><div class="vcep-met-val">${fmtKm(s.dist_minima)}</div><div class="vcep-met-lbl">km do mais próximo</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.pontos_mesma_zona}</div><div class="vcep-met-lbl">pts mesma zona</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.total_pontos || 0}</div><div class="vcep-met-lbl">pontos total</div></div>
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

  const btn = document.getElementById('vcep-btn-add-svc');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Geocodificando...'; }

  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep: cep.replace(/\D/g, ''),
        numero:        document.getElementById('vadd-num')?.value || '',
        cliente:       document.getElementById('vadd-cli')?.value || '',
        descricao:     document.getElementById('vadd-desc')?.value || '',
        tipo_aparelho: document.getElementById('vadd-tipo')?.value || '',
        modelo:        document.getElementById('vadd-modelo')?.value || '',
      }),
    });

    toast(`Ponto adicionado! ${fmtKm(r.distancia_total)} km`, 'success');
    if (r.aviso) toast(r.aviso, 'info');

    mostrarDetalhe();

    await renderFichaDetalhe(parseInt(fichaId, 10));
    await carregarTecnicos();
    document.getElementById('verificar-resultado').innerHTML = '';
    document.getElementById('verificar-cep-input').value = '';

  } catch (e) {
    toast(e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = 'Adicionar ponto + otimizar rota'; }
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

  const btn = document.getElementById('btn-add-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Geocodificando...';

  // Valida antes de chamar o servidor. O backend também recusa, mas avisar
  // aqui evita o usuário perder o formulário preenchido numa ida e volta.
  const setorEscolhido = document.getElementById('add-setor').value;
  if (!setorEscolhido) {
    toast('Escolha o setor do atendimento.', 'error');
    document.getElementById('add-setor').focus();
    return;
  }

  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep,
        numero:        document.getElementById('add-numero').value,
        cliente:       document.getElementById('add-cliente').value,
        descricao:     document.getElementById('add-descricao').value,
        tipo_aparelho: document.getElementById('add-tipo-aparelho').value,
        modelo:        document.getElementById('add-modelo').value,
        numero_os:     document.getElementById('add-numero-os').value,
        setor_id:      setorEscolhido,
      }),
    });

    lembrarSetor(setorEscolhido);

    fecharModais();
    toast(`Ponto adicionado! Distância estimada: ${fmtKm(r.distancia_total)} km`, 'success');
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
  if (!confirm('Remover este ponto do roteiro?')) return;

  const row = document.getElementById('svc-' + servicoId);
  if (row) row.style.opacity = '0.4';

  try {
    const r = await api(`/servicos/${servicoId}`, { method: 'DELETE' });
    toast(`Ponto removido. ${fmtKm(r.distancia_total)} km`, 'success');
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

async function alternarStatusServico(servicoId, novoStatus, fichaId) {
  try {
    await api(`/servicos/${servicoId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status: novoStatus }),
    });
    toast(novoStatus === 'concluido' ? 'Ponto marcado como feito' : 'Ponto reaberto', 'success');
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
  ['add-cep','add-numero','add-cliente','add-descricao','add-tipo-aparelho','add-modelo','add-numero-os']
    .forEach(id => { document.getElementById(id).value = ''; });
  preencherSelectSetor('add-setor');
  document.getElementById('modal-add-servico').classList.add('open');
  setTimeout(() => document.getElementById('add-cep').focus(), 100);
}

function abrirModalEditarServico(servicoId) {
  const s = servicosAtuais.find(x => x.id === servicoId);
  if (!s) { toast('Ponto não encontrado — recarregue a ficha', 'error'); return; }

  document.getElementById('edit-servico-id').value = servicoId;
  document.getElementById('edit-ficha-id').value = fichaAtiva?.id || '';
  document.getElementById('edit-cep').value = formatCEP(s.cep);
  document.getElementById('edit-numero').value = s.numero || '';
  document.getElementById('edit-cliente').value = s.cliente || '';
  document.getElementById('edit-tipo-aparelho').value = s.tipo_aparelho || '';
  document.getElementById('edit-modelo').value = s.modelo || '';
  document.getElementById('edit-numero-os').value = s.numero_os || '';
  preencherSelectSetor('edit-setor', s.setor_id);
  document.getElementById('edit-descricao').value = s.descricao || '';

  document.getElementById('modal-editar-servico').classList.add('open');
  setTimeout(() => document.getElementById('edit-cliente').focus(), 100);
}

async function salvarEdicaoServico() {
  const servicoId = document.getElementById('edit-servico-id').value;
  const fichaId = document.getElementById('edit-ficha-id').value;
  const cep = document.getElementById('edit-cep').value.replace(/\D/g, '');

  if (cep.length !== 8) { toast('Informe um CEP válido', 'error'); return; }

  const btn = document.getElementById('btn-editar-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Salvando...';

  const setorEditado = document.getElementById('edit-setor').value;
  if (!setorEditado) {
    toast('Escolha o setor do atendimento.', 'error');
    document.getElementById('edit-setor').focus();
    return;
  }

  try {
    await api(`/servicos/${servicoId}`, {
      method: 'PUT',
      body: JSON.stringify({
        cep,
        numero:        document.getElementById('edit-numero').value,
        cliente:       document.getElementById('edit-cliente').value,
        descricao:     document.getElementById('edit-descricao').value,
        tipo_aparelho: document.getElementById('edit-tipo-aparelho').value,
        modelo:        document.getElementById('edit-modelo').value,
        numero_os:     document.getElementById('edit-numero-os').value,
        setor_id:      setorEditado,
      }),
    });

    lembrarSetor(setorEditado);

    fecharModais();
    toast('Ponto atualizado', 'success');
    await renderFichaDetalhe(parseInt(fichaId, 10));
    await carregarTecnicos();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Salvar Alterações';
  }
}

function fecharModais() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
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