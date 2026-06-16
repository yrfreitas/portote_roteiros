// ─── STATE ───────────────────────────────────────────────────────────
let fichaAtiva = null;
let tecnicoAtivo = null;
let tecnicos = [];

// ─── MAPA ────────────────────────────────────────────────────────────
let mapaLeaflet = null;
let mapaMarkers = [];
let mapaPolyline = null;

function inicializarMapa(containerId) {
  if (mapaLeaflet) { mapaLeaflet.remove(); mapaLeaflet = null; }
  mapaMarkers = [];
  mapaPolyline = null;
  const el = document.getElementById(containerId);
  if (!el) return;
  mapaLeaflet = L.map(containerId, { zoomControl: true, attributionControl: false }).setView([-23.55, -46.63], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(mapaLeaflet);
  L.control.attribution({ prefix: '© OSM' }).addTo(mapaLeaflet);
}

function renderizarMapaPontos(ficha, servicos, corTecnico = '#1a6fd4') {
  if (!mapaLeaflet) return;
  mapaMarkers.forEach(m => m.remove());
  mapaMarkers = [];
  if (mapaPolyline) { mapaPolyline.remove(); mapaPolyline = null; }
  const pontos = [];
  const temPartida = ficha.ponto_partida_lat != null && ficha.ponto_partida_lat !== 0;
  if (temPartida) {
    const lat = ficha.ponto_partida_lat, lng = ficha.ponto_partida_lng;
    pontos.push([lat, lng]);
    const icon = L.divIcon({
      className: '',
      html: `<div style="width:36px;height:36px;border-radius:50%;background:#fff8e0;border:2px solid #b87800;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 8px rgba(0,0,0,0.25);">⭐</div>`,
      iconSize: [36, 36], iconAnchor: [18, 18],
    });
    const marker = L.marker([lat, lng], { icon }).addTo(mapaLeaflet)
      .bindPopup(`<b style="color:#b87800;">🏠 Partida</b><br><span style="font-size:12px;">${ficha.ponto_partida || ''}</span>`);
    mapaMarkers.push(marker);
  }
  const ordenados = [...servicos].sort((a, b) => a.ordem - b.ordem);
  ordenados.forEach((s, i) => {
    if (!s.lat || !s.lng || (s.lat === 0 && s.lng === 0)) return;
    pontos.push([s.lat, s.lng]);
    const num = i + 1;
    const cor = corTecnico || '#1a6fd4';
    const icon = L.divIcon({
      className: '',
      html: `<div style="width:34px;height:34px;border-radius:50%;background:${cor};border:2px solid white;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-family:'JetBrains Mono',monospace;">${num}</div>`,
      iconSize: [34, 34], iconAnchor: [17, 17],
    });
    const endLabel = s.numero ? `Nº ${s.numero} · ${s.endereco_completo || ''}` : (s.endereco_completo || '—');
    const marker = L.marker([s.lat, s.lng], { icon }).addTo(mapaLeaflet)
      .bindPopup(`<div style="min-width:180px;"><div style="font-weight:700;color:${cor};font-size:13px;margin-bottom:4px;">📍 Parada ${num}</div><div style="font-family:monospace;font-size:12px;color:#555;margin-bottom:2px;">${formatCEP(s.cep)}</div><div style="font-size:12px;color:#333;">${endLabel}</div>${s.cliente ? `<div style="font-size:11px;color:#777;margin-top:4px;">👤 ${s.cliente}</div>` : ''}${s.descricao ? `<div style="font-size:11px;color:#777;">${s.descricao}</div>` : ''}</div>`);
    mapaMarkers.push(marker);
  });
  if (pontos.length >= 2) {
    mapaPolyline = L.polyline(pontos, { color: corTecnico || '#1a6fd4', weight: 3, opacity: 0.7, dashArray: '6, 6' }).addTo(mapaLeaflet);
  }
  if (pontos.length === 1) mapaLeaflet.setView(pontos[0], 15);
  else if (pontos.length >= 2) mapaLeaflet.fitBounds(pontos, { padding: [32, 32] });
}

function invalidarMapa() {
  if (mapaLeaflet) setTimeout(() => mapaLeaflet.invalidateSize(), 100);
}

// ─── INIT ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const now = new Date();
  document.getElementById('current-date').textContent =
    now.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }).toUpperCase();
  carregarTecnicos();
});

// ─── API ─────────────────────────────────────────────────────────────
const BASE = "";

async function api(path, options = {}) {
  const res = await fetch(BASE + '/api' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.erro || 'Erro desconhecido');
  return data;
}

// ─── DISTÂNCIA E TEMPO ───────────────────────────────────────────────
const VELOCIDADE_MEDIA = 40;
const TEMPO_POR_PARADA = 20;

function distanciaReal(distBruta) { return distBruta; }

function tempoEstimado(distKmReal, numParadas) {
  return Math.round((distKmReal / VELOCIDADE_MEDIA) * 60 + numParadas * TEMPO_POR_PARADA);
}

function formatarTempo(minutos) {
  if (minutos < 60) return `${minutos}min`;
  const h = Math.floor(minutos / 60), m = minutos % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

// ─── TÉCNICOS ────────────────────────────────────────────────────────
async function carregarTecnicos() {
  try {
    tecnicos = await api('/tecnicos');
    const list = document.getElementById('sidebar-list');
    if (tecnicos.length === 0) {
      list.innerHTML = `<div style="padding:20px 14px;color:var(--text-muted);font-size:12px;text-align:center;">Nenhum técnico cadastrado.<br>Clique em + para adicionar.</div>`;
      return;
    }
    list.innerHTML = tecnicos.map(t => `
      <div class="tecnico-section" id="tecnico-section-${t.id}">
        <div class="tecnico-header" style="border-left:3px solid ${t.cor}">
          <div class="tecnico-nome" style="color:${t.cor}">${t.nome}</div>
          <div class="tecnico-actions">
            <button class="btn-add-ficha" onclick="abrirModalNovaFicha(${t.id})" title="Nova ficha">+ Ficha</button>
            <button class="btn-del-tecnico" onclick="deletarTecnico(event,${t.id})" title="Remover técnico">✕</button>
          </div>
        </div>
        <div class="fichas-do-tecnico" id="fichas-tecnico-${t.id}">
          <div class="loading-row" style="padding:8px 14px;font-size:11px;">Carregando...</div>
        </div>
      </div>
    `).join('');
    for (const t of tecnicos) await carregarFichasTecnico(t.id);
  } catch (e) {
    toast('Erro ao carregar técnicos', 'error');
  }
}

async function carregarFichasTecnico(tecnicoId) {
  try {
    const fichas = await api(`/fichas?tecnico_id=${tecnicoId}`);
    const container = document.getElementById(`fichas-tecnico-${tecnicoId}`);
    if (!container) return;
    if (fichas.length === 0) {
      container.innerHTML = `<div style="padding:8px 14px;color:var(--text-muted);font-size:11px;">Nenhuma ficha ainda.</div>`;
      return;
    }
    const tecnico = tecnicos.find(t => t.id === tecnicoId);
    container.innerHTML = fichas.map(f => `
      <div class="ficha-item ${fichaAtiva?.id === f.id ? 'active' : ''}"
           onclick="selecionarFicha(${f.id})"
           id="sidebar-item-${f.id}"
           style="${fichaAtiva?.id === f.id ? `border-color:${tecnico?.cor}` : ''}">
        <button class="btn-del-ficha" onclick="deletarFicha(event,${f.id})">✕</button>
        <div class="ficha-item-dia">${f.dia_semana}</div>
        <div class="ficha-item-meta">
          ${f.data_referencia ? `<span>${formatarData(f.data_referencia)}</span>` : ''}
          <span class="badge ${f.total_servicos > 0 ? 'accent' : ''}">${f.total_servicos} ponto${f.total_servicos !== 1 ? 's' : ''}</span>
          ${f.distancia_total > 0 ? `<span class="badge">${distanciaReal(f.distancia_total).toFixed(1)} km</span>` : ''}
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error('Erro ao carregar fichas do técnico', tecnicoId, e);
  }
}

async function criarTecnico() {
  const nome = document.getElementById('novo-tecnico-nome').value.trim();
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
  await api(`/tecnicos/${id}`, { method: 'DELETE' });
  if (fichaAtiva?.tecnico_id === id) {
    fichaAtiva = null;
    document.getElementById('empty-state').style.display = 'flex';
    document.getElementById('ficha-detail').style.display = 'none';
  }
  await carregarTecnicos();
  toast('Técnico removido', 'info');
}

// ─── FICHAS ──────────────────────────────────────────────────────────
async function selecionarFicha(id) {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('ficha-detail').style.display = 'block';
  await renderFichaDetalhe(id);
}

async function renderFichaDetalhe(id) {
  const detail = document.getElementById('ficha-detail');
  detail.innerHTML = `<div class="loading-row" style="height:200px;display:flex;align-items:center;justify-content:center;gap:10px;"><div class="spinner"></div><span style="color:var(--text-muted);">Carregando roteiro...</span></div>`;
  if (mapaLeaflet) { mapaLeaflet.remove(); mapaLeaflet = null; }
  const { ficha, servicos } = await api(`/fichas/${id}`);
  fichaAtiva = ficha;
  const tecnico = tecnicos.find(t => t.id === ficha.tecnico_id);
  const corTecnico = tecnico?.cor || 'var(--accent)';
  const temPartida = ficha.ponto_partida_lat != null && ficha.ponto_partida_lat !== 0;
  const distBruta = ficha.distancia_total || 0;
  const distReal = distanciaReal(distBruta);
  const tempo = tempoEstimado(distReal, servicos.length);
  const temCoordenadas = temPartida || servicos.some(s => s.lat && s.lng && (s.lat !== 0 || s.lng !== 0));

  detail.innerHTML = `
    <div class="ficha-header">
      <div>
        <div style="font-size:11px;font-weight:600;color:${corTecnico};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">👤 ${tecnico?.nome || '—'}</div>
        <div class="ficha-titulo">${ficha.dia_semana}</div>
        <div class="ficha-sub">${ficha.data_referencia ? `📅 ${formatarData(ficha.data_referencia)} · ` : ''}Criado em ${formatarDataHora(ficha.created_at)}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <button class="btn btn-primary" onclick="abrirModalAddServico(${ficha.id})">+ Adicionar Ponto</button>
        <button class="btn btn-ghost" id="btn-abrir-maps" style="display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          Abrir no Google Maps
        </button>
      </div>
    </div>
    <div class="stats-strip">
      <div class="stat-card"><div class="stat-label">Pontos de Serviço</div><div class="stat-value" style="color:${corTecnico}">${servicos.length}<span class="stat-unit">pts</span></div></div>
      <div class="stat-card"><div class="stat-label">Distância Estimada</div><div class="stat-value" style="color:${corTecnico}">${distReal > 0 ? distReal.toFixed(1) : '—'}<span class="stat-unit">km</span></div></div>
      <div class="stat-card"><div class="stat-label">Tempo Total (c/ serviços)</div><div class="stat-value" style="color:${corTecnico}">${distReal > 0 ? formatarTempo(tempo) : '—'}<span class="stat-unit"></span></div></div>
    </div>
    <div class="content-map-grid">
      <div class="content-col">
        <div class="panel-grid">
          <div class="panel">
            <div class="panel-header"><div class="panel-icon">🏠</div><span class="panel-title">Ponto de Partida</span></div>
            <div class="panel-body">
              ${temPartida
                ? `<div style="font-family:var(--font-mono);font-size:13px;color:${corTecnico};margin-bottom:4px;">${ficha.ponto_partida_cep || '—'}</div><div style="font-size:12px;color:var(--text-secondary);">${ficha.ponto_partida || 'Endereço não informado'}</div><div style="margin-top:12px;"><a href="https://www.openstreetmap.org/?mlat=${ficha.ponto_partida_lat}&mlon=${ficha.ponto_partida_lng}&zoom=15" target="_blank" style="font-size:11px;color:${corTecnico};text-decoration:none;">↗ Ver no mapa</a></div>`
                : `<div style="color:var(--text-muted);font-size:12px;">Nenhum ponto de partida configurado.</div>`}
            </div>
          </div>
          <div class="panel">
            <div class="panel-header"><div class="panel-icon">⚡</div><span class="panel-title">Otimização de Rota</span></div>
            <div class="panel-body">
              ${temPartida
                ? `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:14px;">Algoritmo <strong>Nearest Neighbor</strong> recalcula automaticamente ao adicionar ou remover pontos.<br><br><span style="color:var(--text-muted);font-size:11px;">ℹ️ Distância estimada por ruas (linha reta × 1.4) · Velocidade média: ${VELOCIDADE_MEDIA} km/h · ${TEMPO_POR_PARADA} min por parada</span></div><button class="btn btn-ghost btn-full" onclick="forcarOtimizacao(${ficha.id})">🔄 Recalcular Rota Agora</button>`
                : `<div style="font-size:12px;color:var(--text-muted);">Adicione um CEP de partida para ativar a otimização.</div>`}
            </div>
          </div>
        </div>
        <div class="roteiro-container">
          <div class="roteiro-header">
            <span class="roteiro-title">🗺️ Roteiro Ordenado</span>
            ${servicos.length > 0 ? `<span class="badge accent">${servicos.length} parada${servicos.length !== 1 ? 's' : ''}</span>` : ''}
          </div>
          ${renderRoteiro(ficha, servicos, corTecnico)}
        </div>
      </div>
      <div class="mapa-col">
        <div class="mapa-wrapper">
          <div class="mapa-header">
            <div class="panel-icon">🗺</div>
            <span class="panel-title">Mapa do Roteiro</span>
            ${temCoordenadas ? `<span class="badge accent" style="margin-left:auto;">${servicos.length} ponto${servicos.length !== 1 ? 's' : ''}</span>` : ''}
          </div>
          <div id="mapa-roteiro" class="mapa-container">
            ${!temCoordenadas ? `<div class="mapa-empty"><div style="font-size:28px;margin-bottom:8px;">📍</div><div style="font-size:12px;color:var(--text-muted);">Adicione pontos com<br>coordenadas para ver o mapa</div></div>` : ''}
          </div>
        </div>
      </div>
    </div>`;

  const btnMaps = document.getElementById('btn-abrir-maps');
  if (btnMaps) btnMaps.addEventListener('click', () => abrirRotaGoogleMaps(ficha, servicos));
  if (temCoordenadas) { inicializarMapa('mapa-roteiro'); renderizarMapaPontos(ficha, servicos, corTecnico); }
}

function renderRoteiro(ficha, servicos, corTecnico = 'var(--accent)') {
  if (servicos.length === 0) {
    return `<div class="loading-row" style="padding:40px;text-align:center;"><div style="font-size:24px;margin-bottom:8px;">📍</div><div>Nenhum ponto adicionado ainda.</div><div style="font-size:11px;margin-top:4px;color:var(--text-muted);">Clique em "+ Adicionar Ponto" para montar o roteiro.</div></div>`;
  }
  const partida = ficha.ponto_partida ? `<div class="partida-strip"><div class="step-num partida">⭐</div><div><div class="partida-label">Ponto de Partida</div><div class="partida-text">${ficha.ponto_partida}</div></div></div>` : '';
  const items = [...servicos].sort((a, b) => a.ordem - b.ordem).map((s, i) => `
    <div class="roteiro-item" id="svc-${s.id}">
      <div class="step-num" style="background:${corTecnico}20;border-color:${corTecnico}60;color:${corTecnico}">${i + 1}</div>
      <div class="roteiro-info">
        <div class="roteiro-cep" style="color:${corTecnico}">${formatCEP(s.cep)}</div>
        <div class="roteiro-endereco">${s.numero ? `<strong>Nº ${s.numero}</strong> · ` : ''}${s.endereco_completo || '—'}</div>
        ${s.cliente ? `<div class="roteiro-cliente">👤 ${s.cliente}${s.descricao ? ' · ' + s.descricao : ''}</div>` : ''}
      </div>
      <div class="roteiro-actions">
        <a href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lng}&zoom=16" target="_blank" style="color:${corTecnico};font-size:11px;text-decoration:none;padding:4px 8px;">🗺</a>
        <button class="btn-remove" onclick="removerServico(${s.id},${ficha.id})">✕</button>
      </div>
    </div>
  `).join('');
  return partida + items;
}

// ─── GOOGLE MAPS ─────────────────────────────────────────────────────
function abrirRotaGoogleMaps(ficha, servicos) {
  const ordenados = [...servicos].sort((a, b) => (a.ordem ?? 999) - (b.ordem ?? 999)).filter(s => s.endereco_completo);
  if (ordenados.length === 0) { toast('Nenhum ponto com endereço válido', 'error'); return; }
  function endTexto(s) {
    let end = s.endereco_completo || '';
    if (s.numero) { const idx = end.indexOf(','); end = idx !== -1 ? end.slice(0, idx) + ', ' + s.numero + end.slice(idx) : end + ', ' + s.numero; }
    if (s.cep) end += `, ${formatCEP(s.cep)}`;
    return end;
  }
  const temPartida = ficha.ponto_partida && ficha.ponto_partida.trim();
  let origin, destination, waypointList;
  if (temPartida) {
    const partidaEnd = ficha.ponto_partida_cep ? `${ficha.ponto_partida}, ${formatCEP(ficha.ponto_partida_cep)}` : ficha.ponto_partida;
    origin = partidaEnd; destination = endTexto(ordenados[ordenados.length - 1]); waypointList = ordenados.slice(0, -1).map(endTexto);
  } else {
    origin = endTexto(ordenados[0]); destination = endTexto(ordenados[ordenados.length - 1]); waypointList = ordenados.slice(1, -1).map(endTexto);
  }
  const params = new URLSearchParams({ api: '1', origin, destination, travelmode: 'driving' });
  let url = `https://www.google.com/maps/dir/?${params.toString()}`;
  if (waypointList.length > 0) url += `&waypoints=${waypointList.map(encodeURIComponent).join('|')}`;
  window.open(url, '_blank', 'noopener,noreferrer');
}

// ─── VERIFICADOR DE CEP ──────────────────────────────────────────────
let verificacaoAtual = null;
let vcepTabAtual = 'analise';
let vcepExpandido = null;

const ZONA_LABEL = {
  centro: 'Centro', norte: 'Zona Norte', sul: 'Zona Sul',
  leste: 'Zona Leste', oeste: 'Zona Oeste', outros: 'Região'
};
const DIAS_SEMANA_FULL = ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado'];
const DIAS_ABREV = {
  'Segunda-feira':'SEG','Terça-feira':'TER','Quarta-feira':'QUA',
  'Quinta-feira':'QUI','Sexta-feira':'SEX','Sábado':'SAB'
};

function _ini(nome) { return nome.trim().split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase(); }
function _hexRgb(h) { return `${parseInt(h.slice(1,3),16)},${parseInt(h.slice(3,5),16)},${parseInt(h.slice(5,7),16)}`; }
function _scoreCor(s) { if (s >= 130) return '#185FA5'; if (s >= 80) return '#0F6E56'; return '#888780'; }
function _scorePalavra(s, rank) {
  if (rank === 0 && s >= 100) return 'Excelente';
  if (s >= 100) return 'Muito bom';
  if (s >= 80) return 'Bom';
  if (s >= 50) return 'Regular';
  return 'Baixo';
}
function _motivos(s, rank) {
  const m = [];
  if (s.mesma_zona) m.push({ tipo:'pos', titulo:'Mesma zona geográfica', desc:`${s.pontos_mesma_zona} de ${s.total_pontos} pts já na ${ZONA_LABEL[s.zona_alvo] || 'mesma zona'}` });
  if (s.dist_minima <= 10) m.push({ tipo:'pos', titulo:'Ponto muito próximo', desc:`${s.dist_minima.toFixed(1)} km do ponto mais próximo nessa rota` });
  else if (s.dist_minima <= 20) m.push({ tipo:'neu', titulo:'Distância moderada', desc:`${s.dist_minima.toFixed(1)} km — aceitável, mas pode aumentar o trajeto` });
  else m.push({ tipo:'neg', titulo:'Distância alta', desc:`${s.dist_minima.toFixed(1)} km — pode desviar significativamente a rota` });
  if (s.total_pontos >= 10) m.push({ tipo:'neu', titulo:'Rota densa', desc:`${s.total_pontos} pontos nesse dia — verifique a capacidade do técnico` });
  else m.push({ tipo:'pos', titulo:'Rota com espaço', desc:`Apenas ${s.total_pontos} pontos — boa capacidade disponível` });
  if (rank === 0) m.push({ tipo:'pos', titulo:'Melhor opção disponível', desc:'Maior pontuação entre todas as rotas analisadas para esse CEP' });
  else if (rank === 2 && s.dist_minima > 15) m.push({ tipo:'neg', titulo:'Encaixe fraco', desc:'Distância alta — não é a rota prioritária para essa região' });
  return m.slice(0, 4);
}

async function verificarCEP() {
  const cepInput = document.getElementById('verificar-cep-input');
  const cep = cepInput.value;
  if (!cep || cep.replace('-','').length < 8) { toast('Informe um CEP válido', 'error'); return; }
  const btn = document.getElementById('btn-verificar');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';
  const resultado = document.getElementById('verificar-resultado');
  resultado.innerHTML = '';
  vcepTabAtual = 'analise';
  vcepExpandido = null;
  try {
    const r = await api('/verificar-cep', { method: 'POST', body: JSON.stringify({ cep: cep.replace('-','') }) });
    verificacaoAtual = r;
    _renderVcep(resultado, r);
  } catch (e) {
    resultado.innerHTML = `<div class="vcep-erro">${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Verificar';
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
        <div class="vcep-geo-addr">${endCurto}</div>
        <div class="vcep-geo-chips">
          <span class="vcep-chip vcep-chip-zona">${ZONA_LABEL[r.zona] || r.zona}</span>
          <span class="vcep-chip vcep-chip-cep">${formatCEP(r.cep || '')}</span>
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
  if (!painel) return;
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

function _vcepAnalise(r) {
  if (!r.sugestoes || r.sugestoes.length === 0) {
    return `<div class="vcep-empty"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><p>Nenhuma rota cadastrada.<br>Use "Novo dia" para criar a primeira.</p></div>`;
  }
  const max = Math.max(...r.sugestoes.map(s => s.score), 1);
  const cards = r.sugestoes.map((s, i) => {
    const sc = Math.round(s.score);
    const isTop = i === 0 && r.tem_boa_opcao;
    const cor = _scoreCor(s.score);
    return `
      <div class="vcep-rota-card${isTop ? ' vcep-rota-top' : ''}" id="vcep-rc-${i}" onclick="vcepToggleCard(${i})">
        <div class="vcep-rota-inner">
          <div class="vcep-avatar" style="background:rgba(${_hexRgb(s.tecnico_cor)},.13);color:${s.tecnico_cor}">
            ${_ini(s.tecnico_nome)}
            <span class="vcep-avatar-rank">${i + 1}</span>
          </div>
          <div class="vcep-rota-info">
            <div class="vcep-rota-nome">${s.tecnico_nome}</div>
           <div class="vcep-rota-dia">${s.dia_semana}${s.data_referencia ? ' · ' + formatarData(s.data_referencia) : ''} · ${s.total_pontos || 0} pts</div>
          </div>
          <div class="vcep-rota-score">
            <div class="vcep-score-num" style="color:${cor}">${sc}</div>
            <div class="vcep-score-bar"><div class="vcep-score-fill" style="width:${Math.round((s.score/max)*100)}%;background:${cor}"></div></div>
            ${isTop ? `<span class="vcep-badge-ideal">IDEAL</span>` : (s.score >= 80 ? `<span class="vcep-badge-bom">${_scorePalavra(s.score,i)}</span>` : '')}
          </div>
        </div>
        <div class="vcep-rota-detalhe" id="vcep-det-${i}" style="display:none"></div>
      </div>`;
  }).join('');
  return `<div class="vcep-analise-wrap"><div class="vcep-analise-label">${r.sugestoes.length} rota${r.sugestoes.length !== 1 ? 's' : ''} analisadas · score 0–200</div>${cards}</div>`;
}

function vcepToggleCard(i) {
  if (vcepExpandido === i) {
    vcepExpandido = null;
    document.getElementById('vcep-det-' + i).style.display = 'none';
    document.getElementById('vcep-rc-' + i).classList.remove('vcep-rota-expanded');
    return;
  }
  if (vcepExpandido !== null) {
    document.getElementById('vcep-det-' + vcepExpandido).style.display = 'none';
    document.getElementById('vcep-rc-' + vcepExpandido)?.classList.remove('vcep-rota-expanded');
  }
  vcepExpandido = i;
  _vcepExpandir(i, verificacaoAtual);
}

function _vcepExpandir(i, r) {
  const s = r.sugestoes[i];
  const el = document.getElementById('vcep-det-' + i);
  const card = document.getElementById('vcep-rc-' + i);
  if (!el || !s) return;
  card?.classList.add('vcep-rota-expanded');
  const ms = _motivos(s, i);
  const icones = { pos: '✓', neu: '~', neg: '✕' };
  const motHtml = ms.map(m => `
    <div class="vcep-motivo vcep-motivo-${m.tipo}">
      <div class="vcep-motivo-icon vcep-motivo-icon-${m.tipo}">${icones[m.tipo]}</div>
      <div>
        <div class="vcep-motivo-titulo">${m.titulo}</div>
        <div class="vcep-motivo-desc">${m.desc}</div>
      </div>
    </div>`).join('');
  el.innerHTML = `
    <div class="vcep-detalhe-body">
      <div class="vcep-detalhe-titulo">Por que essa pontuação?</div>
      <div class="vcep-motivos">${motHtml}</div>
      <div class="vcep-metricas">
        <div class="vcep-metrica"><div class="vcep-met-val">${s.dist_minima.toFixed(1)}</div><div class="vcep-met-lbl">km do mais próximo</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.pontos_mesma_zona}</div><div class="vcep-met-lbl">pts mesma zona</div></div>
        <div class="vcep-metrica"><div class="vcep-met-val">${s.total_pontos || 0}</div><div class="vcep-met-lbl">pontos total</div></div>
      </div>
      <button class="vcep-btn-add" onclick="event.stopPropagation();vcepSwitchTab('add');setTimeout(()=>{const sel=document.getElementById('vcep-rota-sel');if(sel)sel.value=${s.ficha_id};},50)">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Adicionar CEP a essa rota
      </button>
    </div>`;
  el.style.display = 'block';
}

function _vcepAdd(r) {
  if (!r.sugestoes || r.sugestoes.length === 0) {
    return `<div class="vcep-empty"><p>Nenhuma rota disponível.<br>Crie um novo dia primeiro.</p></div>`;
  }
  const cepFmt = formatCEP(r.cep || '');
  const opts = r.sugestoes.map(s =>
    `<option value="${s.ficha_id}">${s.tecnico_nome} — ${s.dia_semana} (score ${Math.round(s.score)})</option>`
  ).join('');
  return `
    <div class="vcep-form">
      <div class="vcep-form-titulo">Adicionar ${cepFmt} a uma rota existente</div>
      <div class="vcep-form-grid">
        <div class="vcep-fg vcep-fg-half">
          <label class="vcep-lbl">CEP</label>
          <input class="vcep-input" type="text" id="vadd-cep" value="${cepFmt}" style="font-family:var(--font-mono);letter-spacing:1px">
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
          <label class="vcep-lbl">Descrição</label>
          <input class="vcep-input" type="text" id="vadd-desc" placeholder="Ex: não gela">
        </div>
      </div>
      <button class="vcep-btn-primary" onclick="vcepAdicionarServico()">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        Adicionar ponto + otimizar rota
      </button>
    </div>`;
}

function _vcepNovoDia(r) {
  const cepFmt = formatCEP(r.cep || '');
  const tOpts = (r.tecnicos || []).map(t => `<option value="${t.id}">${t.nome}</option>`).join('');
  const dPills = DIAS_SEMANA_FULL.map(d => `<button type="button" class="vcep-dpill" data-dia="${d}">${DIAS_ABREV[d]}</button>`).join('');
  const aviso = !r.tem_boa_opcao
    ? `<div class="vcep-aviso">Nenhuma rota tem bom encaixe para ${ZONA_LABEL[r.zona] || r.zona}. Criar um dia dedicado melhora a eficiência da região.</div>`
    : '';
  return `
    <div class="vcep-form">
      <div class="vcep-form-titulo">Criar novo dia e adicionar ${cepFmt}</div>
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
          <input class="vcep-input" type="text" id="vnovo-cep" placeholder="01310-100" style="font-family:var(--font-mono)" oninput="formatarCEP(this)">
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
        Criar dia + adicionar ${cepFmt}
      </button>
    </div>`;
}

async function vcepAdicionarServico() {
  if (!verificacaoAtual) return;
  const fichaId = document.getElementById('vcep-rota-sel')?.value;
  const cep = document.getElementById('vadd-cep')?.value;
  if (!fichaId || !cep) { toast('Preencha os campos obrigatórios', 'error'); return; }
  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep: cep.replace('-',''),
        numero: document.getElementById('vadd-num')?.value || '',
        cliente: document.getElementById('vadd-cli')?.value || '',
        descricao: document.getElementById('vadd-desc')?.value || ''
      })
    });
    toast(`Ponto adicionado! ${distanciaReal(r.distancia_total).toFixed(1)} km`, 'success');
    await renderFichaDetalhe(parseInt(fichaId));
    await carregarTecnicos();
    document.getElementById('verificar-resultado').innerHTML = '';
  } catch (e) { toast(e.message, 'error'); }
}

async function vcepCriarNovoDia() {
  if (!verificacaoAtual) return;
  const tecnicoSelect = document.getElementById('vnovo-tec');
  const diaSelecionado = document.querySelector('#vcep-dias-novo .vcep-dpill.sel');
  if (!tecnicoSelect?.value) { toast('Selecione um técnico', 'error'); return; }
  if (!diaSelecionado) { toast('Selecione um dia da semana', 'error'); return; }
  const body = {
    tecnico_id: parseInt(tecnicoSelect.value),
    dia_semana: diaSelecionado.dataset.dia,
    data_referencia: document.getElementById('vnovo-data')?.value || '',
    ponto_partida: document.getElementById('vnovo-base')?.value || '',
    ponto_partida_cep: (document.getElementById('vnovo-cep')?.value || '').replace('-','')
  };
  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify(body) });
    toast(`Ficha "${body.dia_semana}" criada!`, 'success');
    await carregarTecnicos();
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('ficha-detail').style.display = 'block';
    await renderFichaDetalhe(r.id);
    document.getElementById('add-ficha-id').value = r.id;
    document.getElementById('add-cep').value = formatCEP(verificacaoAtual.cep);
    document.getElementById('add-numero').value = '';
    document.getElementById('add-cliente').value = '';
    document.getElementById('add-descricao').value = '';
    document.getElementById('modal-add-servico').classList.add('open');
    setTimeout(() => document.getElementById('add-numero').focus(), 150);
  } catch (e) { toast(e.message, 'error'); }
}

// ─── AÇÕES ───────────────────────────────────────────────────────────
async function criarFicha() {
  const dia = document.getElementById('nova-dia').value;
  const tecnicoId = document.getElementById('nova-ficha-tecnico-id').value;
  if (!dia) { toast('Selecione um dia da semana', 'error'); return; }
  const body = {
    tecnico_id: parseInt(tecnicoId),
    dia_semana: dia,
    data_referencia: document.getElementById('nova-data').value,
    ponto_partida: document.getElementById('nova-partida-nome').value,
    ponto_partida_cep: document.getElementById('nova-partida-cep').value.replace('-','')
  };
  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify(body) });
    fecharModais();
    toast(`Ficha "${dia}" criada!`, 'success');
    await carregarTecnicos();
    selecionarFicha(r.id);
  } catch (e) { toast(e.message, 'error'); }
}

async function deletarFicha(evt, id) {
  evt.stopPropagation();
  if (!confirm('Remover esta ficha e todos os seus serviços?')) return;
  await api(`/fichas/${id}`, { method: 'DELETE' });
  if (fichaAtiva?.id === id) {
    fichaAtiva = null;
    document.getElementById('empty-state').style.display = 'flex';
    document.getElementById('ficha-detail').style.display = 'none';
  }
  await carregarTecnicos();
  toast('Ficha removida', 'info');
}

async function adicionarServico() {
  const fichaId = document.getElementById('add-ficha-id').value;
  const cep = document.getElementById('add-cep').value;
  if (!cep || cep.replace('-','').length < 8) { toast('Informe um CEP válido', 'error'); return; }
  const btn = document.getElementById('btn-add-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Geocodificando...';
  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep: cep.replace('-',''),
        numero: document.getElementById('add-numero').value,
        cliente: document.getElementById('add-cliente').value,
        descricao: document.getElementById('add-descricao').value
      })
    });
    fecharModais();
    toast(`Ponto adicionado! Distância estimada: ${distanciaReal(r.distancia_total).toFixed(1)} km`, 'success');
    if (r.aviso) toast(r.aviso, 'info');
    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
  finally { btn.disabled = false; btn.innerHTML = 'Adicionar + Otimizar'; }
}

async function removerServico(servicoId, fichaId) {
  if (!confirm('Remover este ponto do roteiro?')) return;
  const row = document.getElementById('svc-' + servicoId);
  if (row) row.style.opacity = '0.4';
  try {
    const r = await api(`/servicos/${servicoId}`, { method: 'DELETE' });
    toast(`Ponto removido. ${distanciaReal(r.distancia_total).toFixed(1)} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); if (row) row.style.opacity = '1'; }
}

async function forcarOtimizacao(fichaId) {
  try {
    const r = await api(`/fichas/${fichaId}/otimizar`, { method: 'POST' });
    toast(`Rota otimizada! ${distanciaReal(r.distancia_total).toFixed(1)} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarTecnicos();
  } catch (e) { toast(e.message, 'error'); }
}

// ─── MODAIS ──────────────────────────────────────────────────────────
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
  document.getElementById('add-cep').value = '';
  document.getElementById('add-numero').value = '';
  document.getElementById('add-cliente').value = '';
  document.getElementById('add-descricao').value = '';
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

// ─── HELPERS ─────────────────────────────────────────────────────────
function selecionarDia(el, dia) {
  document.querySelectorAll('.dia-pill').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('nova-dia').value = dia;
}
function formatarCEP(input) {
  let v = input.value.replace(/\D/g, '');
  if (v.length > 5) v = v.slice(0, 5) + '-' + v.slice(5, 8);
  input.value = v;
}
function formatCEP(cep) {
  if (!cep) return '—';
  const c = cep.replace(/\D/g, '');
  return c.length === 8 ? c.slice(0, 5) + '-' + c.slice(5) : cep;
}
function formatarData(d) {
  if (!d) return '';
  const [y, m, day] = d.split('-');
  return `${day}/${m}/${y}`;
}
function formatarDataHora(dt) {
  if (!dt) return '';
  const d = new Date(dt + (dt.includes('Z') ? '' : 'Z'));
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}
function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const cor = type === 'success' ? 'var(--success-text)' : type === 'error' ? 'var(--danger-text)' : 'var(--accent-text)';
  el.innerHTML = `<span style="font-weight:600;color:${cor};">${icons[type]}</span> ${msg}`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 300); }, 4000);
}