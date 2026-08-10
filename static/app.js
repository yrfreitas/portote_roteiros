let fichaAtiva   = null;
let tecnicoAtivo = null;
let tecnicos     = [];

// ===== ÍCONES (SVG de linha, não emoji) =====
// Emoji como ícone de interface é o maior sinal visual de "feito às pressas
// por IA". Um único jogo de ícones consistente (estilo Feather: 24x24,
// stroke, sem preenchimento) resolve isso de vez — mesma linguagem visual
// em toda a tela, em vez de depender da fonte de emoji do sistema.
const ICONES = {
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

document.addEventListener('DOMContentLoaded', () => {
  iniciarRelogio();
  iniciarMonitorSaude();
  carregarTecnicos();
  _vcepRenderHistorico();
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
  const isCep = tab === 'cep';

  document.getElementById('panel-roteiros-sidebar').style.display = isCep ? 'none' : 'flex';
  document.getElementById('panel-roteiros-main').style.display = isCep ? 'none' : 'block';
  document.getElementById('panel-cep').style.display = isCep ? 'block' : 'none';

  document.getElementById('mtab-roteiros').classList.toggle('active', !isCep);
  document.getElementById('mtab-cep').classList.toggle('active', isCep);

  // Foco automático no campo de CEP ao abrir a aba, pra já poder digitar
  if (isCep) {
    setTimeout(() => document.getElementById('verificar-cep-input')?.focus(), 80);
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

    if (!res.ok) throw new Error(data.erro || `Erro ${res.status}`);
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
      <div class="tecnico-section" id="tecnico-section-${t.id}">
        <div class="tecnico-header" style="border-left:3px solid ${escCor(t.cor)}">
          <div class="tecnico-nome" style="color:${escCor(t.cor)}">${esc(t.nome)}</div>
          <div class="tecnico-actions">
            <button class="btn-add-ficha" onclick="abrirModalNovaFicha(${t.id})" title="Nova ficha">+ Ficha</button>
            <button class="btn-del-tecnico" onclick="deletarTecnico(event,${t.id})" title="Remover técnico">${icone('x', 'icone-11')}</button>
          </div>
        </div>
        <div class="fichas-do-tecnico" id="fichas-tecnico-${t.id}">
          <div class="loading-row" style="padding:8px 14px;font-size:11px;">Carregando...</div>
        </div>
      </div>
    `).join('');

    await Promise.all(tecnicos.map(t => carregarFichasTecnico(t.id)));

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
    const fichas = await api(`/fichas?tecnico_id=${tecnicoId}`);

    if (fichas.length === 0) {
      container.innerHTML = `<div style="padding:8px 14px;color:var(--text-muted);font-size:11px;">Nenhuma ficha ainda.</div>`;
      return;
    }

    const tecnico = tecnicos.find(t => t.id === tecnicoId);

    container.innerHTML = fichas.map(f => {
      const ativa = fichaAtiva?.id === f.id;
      return `
      <div class="ficha-item ${ativa ? 'active' : ''}"
           onclick="selecionarFicha(${f.id})"
           id="sidebar-item-${f.id}"
           style="${ativa ? `border-color:${escCor(tecnico?.cor)}` : ''}">
        <button class="btn-del-ficha" onclick="deletarFicha(event,${f.id})">${icone('x', 'icone-11')}</button>
        <div class="ficha-item-dia">${esc(f.dia_semana)}</div>
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

    const totalRotas  = fichas.length;
    const totalPontos = fichas.reduce((soma, f) => soma + (f.total_servicos || 0), 0);
    const totalKm     = fichas.reduce((soma, f) => soma + (f.distancia_total || 0), 0);

    animarNumero(document.getElementById('vg-tecnicos'), tecnicos.length);
    animarNumero(document.getElementById('vg-rotas'), totalRotas);
    animarNumero(document.getElementById('vg-pontos'), totalPontos);
    animarNumero(document.getElementById('vg-km'), totalKm, {
      formatar: v => v.toFixed(1).replace('.', ','),
    });

    const porTecnico = new Map();
    fichas.forEach(f => {
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
        <div class="ficha-titulo">${esc(ficha.dia_semana)}</div>
        <div class="ficha-sub">${ficha.data_referencia ? `<span style="display:inline-flex;align-items:center;gap:4px;">${icone('calendario', 'icone-12')} ${esc(formatarData(ficha.data_referencia))}</span> · ` : ''}Criado em ${esc(formatarDataHora(ficha.created_at))}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <button class="btn btn-primary" onclick="abrirModalAddServico(${ficha.id})">+ Adicionar Ponto</button>
        <button class="btn btn-ghost" id="btn-abrir-maps" style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          Abrir no Google Maps
        </button>
        <button class="btn btn-ghost" id="btn-whatsapp-rota" style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
          Enviar por WhatsApp
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
    return `
      <div class="roteiro-item" id="svc-${s.id}" data-id="${s.id}">
        <div class="drag-handle" title="Arraste para reordenar">⠿</div>
        <div class="step-num" style="background:${cor}20;border-color:${cor}60;color:${cor}">${i + 1}</div>
        <div class="roteiro-info">
          <div class="roteiro-cep" style="color:${cor}">${esc(formatCEP(s.cep))}</div>
          <div class="roteiro-endereco">${s.numero ? `<strong>Nº ${esc(s.numero)}</strong> · ` : ''}${esc(s.endereco_completo) || '—'}</div>
          ${s.cliente ? `<div class="roteiro-cliente">${icone('usuario', 'icone-11')} ${esc(s.cliente)}${s.descricao ? ' · ' + esc(s.descricao) : ''}</div>` : ''}
          ${aparelho ? `<div class="roteiro-aparelho">${icone('ferramenta', 'icone-11')} ${esc(aparelho)}</div>` : ''}
          ${(!s.lat || !s.lng) ? `<div class="roteiro-cliente" style="color:var(--danger-text);display:flex;align-items:center;gap:4px;">${icone('alerta', 'icone-11')} sem coordenada — fora do cálculo</div>` : ''}
        </div>
        <div class="roteiro-actions">
          ${(s.lat && s.lng) ? `<a href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lng}&zoom=16" target="_blank" rel="noopener" style="color:${cor};padding:4px 8px;display:inline-flex;">${icone('externo', 'icone-13')}</a>` : ''}
          <button class="btn-remove" onclick="removerServico(${s.id},${ficha.id})">${icone('x', 'icone-11')}</button>
        </div>
      </div>`;
  }).join('');

  return partida + `<div class="roteiro-lista" id="roteiro-lista">${items}</div>`;
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
function _encaixeInfo(s, rank, isTop) {
  if (s.vazia) {
    return { texto: 'Rota vazia', classe: 'vazio', cor: 'var(--text-muted)' };
  }
  if (isTop) {
    return { texto: 'Melhor encaixe', classe: 'otimo', cor: 'var(--accent-light)' };
  }
  if (s.score >= 100) {
    return { texto: 'Encaixa bem', classe: 'bom', cor: 'var(--success)' };
  }
  if (s.score >= 50) {
    return { texto: 'Encaixa, mas não é ideal', classe: 'medio', cor: 'var(--gold)' };
  }
  return { texto: 'Não recomendado', classe: 'ruim', cor: 'var(--danger)' };
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

  const max = Math.max(...r.sugestoes.map(s => s.score), 1);

  // Mesmo limite que o backend usa pra penalizar rota lotada na pontuação
  // (CAPACIDADE_IDEAL em routes/tecnicos.py) — aqui só torna isso visível
  // sem precisar expandir o card.
  const CAPACIDADE_IDEAL_ROTA = 8;

  const cards = r.sugestoes.map((s, i) => {
    const sc    = Math.round(s.score);
    const isTop = i === 0 && r.tem_boa_opcao;
    const encaixe = _encaixeInfo(s, i, isTop);
    const distTxt = (s.dist_minima !== null && s.dist_minima !== undefined)
      ? `${fmtKm(s.dist_minima)} km` : '—';

    const dataTxt = s.data_referencia ? ' · ' + formatarData(s.data_referencia) : '';
    const ptsTxt  = s.vazia ? 'rota vazia' : `${s.total_pontos} pts`;
    const lotada  = !s.vazia && s.total_pontos >= CAPACIDADE_IDEAL_ROTA;

    const idCard = `vcep-rc-${prefixo}${i}`;
    const idDet  = `vcep-det-${prefixo}${i}`;

    return `
      <div class="vcep-rota-card${isTop ? ' vcep-rota-top' : ''}" id="${idCard}"
           ${interativo ? `onclick="vcepToggleCard('${prefixo}',${i})"` : ''}>
        <div class="vcep-rota-inner">
          <div class="vcep-avatar" style="background:rgba(${_hexRgb(s.tecnico_cor)},.13);color:${escCor(s.tecnico_cor)}">
            ${esc(_ini(s.tecnico_nome))}
            <span class="vcep-avatar-rank">${i + 1}</span>
          </div>
          <div class="vcep-rota-info">
            <div class="vcep-rota-nome">${esc(s.tecnico_nome)}</div>
            <div class="vcep-rota-dia">
              ${esc(s.dia_semana)} · ${ptsTxt}${esc(dataTxt)}
              ${lotada ? `<span class="vcep-tag-lotada" title="Rota com ${s.total_pontos} pontos — acima da capacidade ideal (${CAPACIDADE_IDEAL_ROTA})">${icone('alerta', 'icone-10')} cheia</span>` : ''}
            </div>
            <div class="vcep-rota-dist">${distTxt !== '—' ? `${distTxt} ${s.vazia ? 'da base' : 'do ponto mais próximo'}` : ''}</div>
          </div>
          <div class="vcep-rota-score">
            <div class="vcep-score-num" style="color:${encaixe.cor}">${sc}</div>
            <div class="vcep-score-bar"><div class="vcep-score-fill" style="width:${Math.round((s.score/max)*100)}%;background:${encaixe.cor}"></div></div>
          </div>
          ${interativo ? `
          <button type="button" class="vcep-btn-add-rapido" title="Adicionar este CEP nessa rota"
                  onclick="event.stopPropagation(); vcepSelecionarRota(${s.ficha_id})">
            ${icone('plus', 'icone-13')}
          </button>` : ''}
        </div>
        <span class="vcep-badge-encaixe vcep-badge-${encaixe.classe}">${esc(encaixe.texto)}</span>
        ${interativo ? `<div class="vcep-rota-detalhe" id="${idDet}" style="display:none"></div>` : ''}
      </div>`;
  }).join('');

  return `<div class="vcep-analise-wrap"><div class="vcep-analise-label">${r.sugestoes.length} rota${r.sugestoes.length !== 1 ? 's' : ''} analisada${r.sugestoes.length !== 1 ? 's' : ''}</div>${cards}</div>`;
}

function vcepToggleCard(prefixo, i) {
  // prefixo só é diferente de '' no modo comparar — que é somente
  // leitura e nem chama isso (evita ids duplicados entre as 2 colunas).
  if (vcepExpandido === i) {
    vcepExpandido = null;
    document.getElementById('vcep-det-' + prefixo + i)?.style.setProperty('display', 'none');
    document.getElementById('vcep-rc-' + prefixo + i)?.classList.remove('vcep-rota-expanded');
    return;
  }
  if (vcepExpandido !== null) {
    document.getElementById('vcep-det-' + prefixo + vcepExpandido)?.style.setProperty('display', 'none');
    document.getElementById('vcep-rc-' + prefixo + vcepExpandido)?.classList.remove('vcep-rota-expanded');
  }
  vcepExpandido = i;
  _vcepExpandir(i, verificacaoAtual, prefixo);
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
      }),
    });

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
  ['add-cep','add-numero','add-cliente','add-descricao','add-tipo-aparelho','add-modelo']
    .forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('modal-add-servico').classList.add('open');
  setTimeout(() => document.getElementById('add-cep').focus(), 100);
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