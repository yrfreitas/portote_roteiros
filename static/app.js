// ─── STATE ───────────────────────────────────────────────────────────
let fichaAtiva = null;
let diasMap = {};

// ─── INIT ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const now = new Date();
  document.getElementById('current-date').textContent =
    now.toLocaleDateString('pt-BR', {
      weekday: 'short', day: '2-digit', month: 'short'
    }).toUpperCase();

  carregarFichas();
});

// ─── API ─────────────────────────────────────────────────────────────
async function api(path, options = {}) {
  const res = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.erro || 'Erro desconhecido');
  return data;
}

// ─── FICHAS ──────────────────────────────────────────────────────────
async function carregarFichas() {
  const fichas = await api('/fichas');
  const list = document.getElementById('sidebar-list');
  diasMap = {};
  fichas.forEach(f => diasMap[f.id] = f);

  if (fichas.length === 0) {
    list.innerHTML = `
      <div style="padding:20px 14px; color:var(--text-muted); font-size:12px; text-align:center;">
        Nenhuma ficha criada.<br>Clique em + para começar.
      </div>`;
    return;
  }

  list.innerHTML = fichas.map(f => `
    <div class="ficha-item ${fichaAtiva?.id === f.id ? 'active' : ''}"
         onclick="selecionarFicha(${f.id})"
         id="sidebar-item-${f.id}">
      <button class="btn-del-ficha" onclick="deletarFicha(event, ${f.id})">✕</button>
      <div class="ficha-item-dia">${f.dia_semana}</div>
      <div class="ficha-item-meta">
        ${f.data_referencia ? `<span>${formatarData(f.data_referencia)}</span>` : ''}
        <span class="badge ${f.total_servicos > 0 ? 'accent' : ''}">
          ${f.total_servicos} ponto${f.total_servicos !== 1 ? 's' : ''}
        </span>
        ${f.distancia_total > 0 ? `<span class="badge">${f.distancia_total} km</span>` : ''}
      </div>
    </div>
  `).join('');
}

async function selecionarFicha(id) {
  fichaAtiva = diasMap[id] || { id };

  document.querySelectorAll('.ficha-item').forEach(el => el.classList.remove('active'));
  const item = document.getElementById('sidebar-item-' + id);
  if (item) item.classList.add('active');

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('ficha-detail').style.display = 'block';

  await renderFichaDetalhe(id);
}

async function renderFichaDetalhe(id) {
  const detail = document.getElementById('ficha-detail');
  detail.innerHTML = `
    <div class="loading-row" style="height:200px; display:flex; align-items:center; justify-content:center; gap:10px;">
      <div class="spinner"></div>
      <span style="color:var(--text-muted);">Carregando roteiro...</span>
    </div>`;

  const { ficha, servicos } = await api(`/fichas/${id}`);
  fichaAtiva = ficha;

  const temPartida = ficha.ponto_partida_lat != null;
  const distTotal = ficha.distancia_total || 0;

  detail.innerHTML = `
    <div class="ficha-header">
      <div>
        <div class="ficha-titulo">${ficha.dia_semana}</div>
        <div class="ficha-sub">
          ${ficha.data_referencia ? `📅 ${formatarData(ficha.data_referencia)} · ` : ''}
          Criado em ${formatarDataHora(ficha.created_at)}
        </div>
      </div>
      <button class="btn btn-primary" onclick="abrirModalAddServico(${ficha.id})">
        + Adicionar Ponto
      </button>
    </div>

    <div class="stats-strip">
      <div class="stat-card">
        <div class="stat-label">Pontos de Serviço</div>
        <div class="stat-value">${servicos.length}<span class="stat-unit">pts</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Distância Total</div>
        <div class="stat-value">
          ${distTotal > 0 ? distTotal.toFixed(1) : '—'}<span class="stat-unit">km</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tempo Estimado</div>
        <div class="stat-value">
          ${distTotal > 0 ? Math.round(distTotal / 30 * 60) : '—'}<span class="stat-unit">min</span>
        </div>
      </div>
    </div>

    <div class="panel-grid">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-icon">🏠</div>
          <span class="panel-title">Ponto de Partida</span>
        </div>
        <div class="panel-body">
          ${temPartida ? `
            <div style="font-family:var(--font-mono); font-size:13px; color:var(--gold); margin-bottom:4px;">
              ${ficha.ponto_partida_cep || '—'}
            </div>
            <div style="font-size:12px; color:var(--text-secondary);">
              ${ficha.ponto_partida || 'Endereço não informado'}
            </div>
            <div style="margin-top:12px;">
              <a href="https://www.openstreetmap.org/?mlat=${ficha.ponto_partida_lat}&mlon=${ficha.ponto_partida_lng}&zoom=15"
                 target="_blank"
                 style="font-size:11px; color:var(--accent-text); text-decoration:none;">
                ↗ Ver no mapa
              </a>
            </div>
          ` : `
            <div style="color:var(--text-muted); font-size:12px;">
              Nenhum ponto de partida configurado.
            </div>
          `}
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div class="panel-icon">⚡</div>
          <span class="panel-title">Otimização de Rota</span>
        </div>
        <div class="panel-body">
          ${temPartida ? `
            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:14px;">
              Algoritmo <strong>Nearest Neighbor</strong> recalcula automaticamente
              ao adicionar ou remover pontos.
            </div>
            <button class="btn btn-ghost btn-full" onclick="forcarOtimizacao(${ficha.id})">
              🔄 Recalcular Rota Agora
            </button>
          ` : `
            <div style="font-size:12px; color:var(--text-muted);">
              Adicione um CEP de partida para ativar a otimização.
            </div>
          `}
        </div>
      </div>
    </div>

    <div class="roteiro-container">
      <div class="roteiro-header">
        <span class="roteiro-title">🗺️ Roteiro Ordenado</span>
        ${servicos.length > 0 ? `<span class="badge accent">${servicos.length} parada${servicos.length !== 1 ? 's' : ''}</span>` : ''}
      </div>
      ${renderRoteiro(ficha, servicos)}
    </div>
  `;
}

function renderRoteiro(ficha, servicos) {
  if (servicos.length === 0) {
    return `
      <div class="loading-row" style="padding:40px;">
        <div style="font-size:24px; margin-bottom:8px;">📍</div>
        <div>Nenhum ponto adicionado ainda.</div>
        <div style="font-size:11px; margin-top:4px; color:var(--text-muted);">
          Clique em "+ Adicionar Ponto" para montar o roteiro.
        </div>
      </div>`;
  }

  const partida = ficha.ponto_partida ? `
    <div class="partida-strip">
      <div class="step-num partida">⭐</div>
      <div>
        <div class="partida-label">Ponto de Partida</div>
        <div class="partida-text">${ficha.ponto_partida}</div>
      </div>
    </div>` : '';

  const items = [...servicos]
    .sort((a, b) => a.ordem - b.ordem)
    .map((s, i) => `
      <div class="roteiro-item" id="svc-${s.id}">
        <div class="step-num">${i + 1}</div>
        <div class="roteiro-info">
          <div class="roteiro-cep">${formatCEP(s.cep)}</div>
          <div class="roteiro-endereco">
            ${s.numero ? `<strong>Nº ${s.numero}</strong> · ` : ''}${s.endereco_completo || '—'}
          </div>
          ${s.cliente ? `<div class="roteiro-cliente">👤 ${s.cliente}${s.descricao ? ' · ' + s.descricao : ''}</div>` : ''}
        </div>
        <div class="roteiro-actions">
          <a href="https://www.openstreetmap.org/?mlat=${s.lat}&mlon=${s.lng}&zoom=16"
             target="_blank"
             style="color:var(--accent-text); font-size:11px; text-decoration:none; padding:4px 8px;">
            🗺
          </a>
          <button class="btn-remove" onclick="removerServico(${s.id}, ${ficha.id})">✕</button>
        </div>
      </div>
    `).join('');

  return partida + items;
}

// ─── AÇÕES ───────────────────────────────────────────────────────────
async function criarFicha() {
  const dia = document.getElementById('nova-dia').value;
  if (!dia) { toast('Selecione um dia da semana', 'error'); return; }

  const body = {
    dia_semana: dia,
    data_referencia: document.getElementById('nova-data').value,
    ponto_partida: document.getElementById('nova-partida-nome').value,
    ponto_partida_cep: document.getElementById('nova-partida-cep').value.replace('-', '')
  };

  try {
    const r = await api('/fichas', { method: 'POST', body: JSON.stringify(body) });
    fecharModais();
    toast(`Ficha "${dia}" criada!`, 'success');
    await carregarFichas();
    selecionarFicha(r.id);
  } catch (e) {
    toast(e.message, 'error');
  }
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
  await carregarFichas();
  toast('Ficha removida', 'info');
}

async function adicionarServico() {
  const fichaId = document.getElementById('add-ficha-id').value;
  const cep = document.getElementById('add-cep').value;

  if (!cep || cep.replace('-', '').length < 8) {
    toast('Informe um CEP válido', 'error');
    return;
  }

  const btn = document.getElementById('btn-add-servico');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Geocodificando...';

  try {
    const r = await api(`/fichas/${fichaId}/servicos`, {
      method: 'POST',
      body: JSON.stringify({
        cep: cep.replace('-', ''),
        numero: document.getElementById('add-numero').value,
        cliente: document.getElementById('add-cliente').value,
        descricao: document.getElementById('add-descricao').value
      })
    });
    fecharModais();
    toast(`Ponto adicionado! Distância total: ${r.distancia_total} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarFichas();
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
    toast(`Ponto removido. Rota recalculada: ${r.distancia_total} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarFichas();
  } catch (e) {
    toast(e.message, 'error');
    if (row) row.style.opacity = '1';
  }
}

async function forcarOtimizacao(fichaId) {
  try {
    const r = await api(`/fichas/${fichaId}/otimizar`, { method: 'POST' });
    toast(`Rota otimizada! Distância: ${r.distancia_total} km`, 'success');
    await renderFichaDetalhe(fichaId);
    await carregarFichas();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ─── MODAIS ──────────────────────────────────────────────────────────
function abrirModalNovaFicha() {
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
  overlay.addEventListener('click', e => {
    if (e.target === overlay) fecharModais();
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') fecharModais();
});

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
  const cor = type === 'success'
    ? 'var(--success-text)'
    : type === 'error'
    ? 'var(--danger-text)'
    : 'var(--accent-text)';
  el.innerHTML = `<span style="font-weight:600; color:${cor};">${icons[type]}</span> ${msg}`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}