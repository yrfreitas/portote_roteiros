// ─── VERIFICADOR DE CEP ──────────────────────────────────────────────
// Adicione este bloco ao final do seu app.js existente

function abrirModalVerificarCep() {
  document.getElementById('checker-cep').value = '';
  document.getElementById('checker-resultado').style.display = 'none';
  document.getElementById('checker-resultado').innerHTML = '';
  document.getElementById('modal-verificar-cep').classList.add('open');
  setTimeout(() => document.getElementById('checker-cep').focus(), 100);
}

async function executarVerificacaoCep() {
  const input = document.getElementById('checker-cep');
  const cep = input.value.replace(/\D/g, '');
  const resultado = document.getElementById('checker-resultado');
  const btn = document.getElementById('btn-checar');

  if (cep.length !== 8) {
    resultado.style.display = 'block';
    resultado.innerHTML = `
      <div class="checker-card checker-warn">
        <span class="checker-icon">⚠</span>
        <span>CEP inválido. Digite os 8 dígitos.</span>
      </div>`;
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div>';
  resultado.style.display = 'block';
  resultado.innerHTML = `
    <div class="checker-card checker-loading">
      <div class="spinner"></div>
      <span>Consultando CEP...</span>
    </div>`;

  try {
    const data = await api('/verificar-cep', {
      method: 'POST',
      body: JSON.stringify({ cep })
    });

    const statusConfig = {
      encaixa:     { cls: 'checker-success', icon: '✓', label: 'Encaixa na rota' },
      possivel:    { cls: 'checker-warn',    icon: '~', label: 'Possível encaixe' },
      nao_encaixa: { cls: 'checker-danger',  icon: '✕', label: 'Não encaixa' },
    };
    const cfg = statusConfig[data.status] || statusConfig.nao_encaixa;

    const fichaHtml = data.ficha_sugerida ? `
      <div class="checker-ficha">
        <div class="checker-ficha-row">
          <span class="checker-ficha-label">Ficha sugerida</span>
          <span class="checker-ficha-value">${data.ficha_sugerida.dia_semana}</span>
        </div>
        <div class="checker-ficha-row">
          <span class="checker-ficha-label">Pontos na rota</span>
          <span class="checker-ficha-value">${data.ficha_sugerida.total_servicos} pts</span>
        </div>
        ${data.ficha_sugerida.distancia_total > 0 ? `
        <div class="checker-ficha-row">
          <span class="checker-ficha-label">Distância atual</span>
          <span class="checker-ficha-value">${Number(data.ficha_sugerida.distancia_total).toFixed(1)} km</span>
        </div>` : ''}
      </div>
    ` : '';

    resultado.innerHTML = `
      <div class="checker-status-bar ${cfg.cls}">
        <span class="checker-status-icon">${cfg.icon}</span>
        <span class="checker-status-label">${cfg.label}</span>
      </div>

      <div class="checker-info-grid">
        <div class="checker-info-item">
          <div class="checker-info-label">CEP</div>
          <div class="checker-info-val mono">${data.cep}</div>
        </div>
        <div class="checker-info-item">
          <div class="checker-info-label">Bairro</div>
          <div class="checker-info-val">${data.bairro || '—'}</div>
        </div>
        <div class="checker-info-item" style="grid-column: 1/-1;">
          <div class="checker-info-label">Endereço</div>
          <div class="checker-info-val">${data.logradouro ? data.logradouro + ', ' : ''}${data.cidade} / ${data.uf}</div>
        </div>
      </div>

      ${fichaHtml}

      <div class="checker-justificativa">
        <div class="checker-just-row">${data.justificativa}</div>
        <div class="checker-just-row bold">${data.sugestao}</div>
      </div>

      ${data.ficha_sugerida ? `
      <button class="btn btn-primary btn-full" style="margin-top:14px;"
        onclick="abrirModalAddServicoComCep(${data.ficha_sugerida.id}, '${data.cep.replace(/\D/g,'')}')">
        + Adicionar à ficha de ${data.ficha_sugerida.dia_semana}
      </button>` : ''}
    `;
  } catch (e) {
    resultado.innerHTML = `
      <div class="checker-card checker-danger">
        <span class="checker-icon">✕</span>
        <span>${e.message}</span>
      </div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Verificar';
  }
}

// Atalho: abre o modal de add serviço já com o CEP preenchido
function abrirModalAddServicoComCep(fichaId, cep) {
  fecharModais();
  abrirModalAddServico(fichaId);
  const input = document.getElementById('add-cep');
  // Formata o CEP antes de preencher
  const formatado = cep.length === 8
    ? cep.slice(0, 5) + '-' + cep.slice(5)
    : cep;
  input.value = formatado;
}