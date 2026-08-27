"""Ordem de Serviço — o documento do atendimento, próprio do site.

Decisão de 2026-08-21: não depende do AgoraOS. A OS é o registro persistente
(cliente, equipamento, defeito, status); QUEM vai atender e QUANDO continuam
sendo respondidos pelo sistema de fichas/técnicos que já existe — a OS só se
liga a um `servico` (routes/servicos.py) em vez de duplicar agenda. Uma OS
pode ter mais de uma visita ligada a ela com o tempo (voltou pra buscar
peça), por isso o vínculo mora em servicos.ordem_servico_id.
"""
import io
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, send_file, session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from routes.clientes import criar_cliente
from routes.estoque import dar_saida
from routes.fichas import obter_ou_criar_ficha, recalcular_rota
from services.geo import geocode_cep

ordens_servico_bp = Blueprint("ordens_servico", __name__)

# Lista fechada — mesma razão de sempre: status alimenta filtro e contagem.
STATUS_OS = [
    "aguardando_agendamento", "agendada", "em_atendimento",
    "aguardando_peca", "aguardando_orcamento", "aguardando_aprovacao",
    "aprovada", "finalizada", "cancelada",
]

TERMOS_PADRAO = (
    "O cliente autoriza a avaliação técnica do equipamento acima descrito. "
    "A taxa de avaliação é devida independentemente da aprovação do orçamento, "
    "salvo acordo em contrário. Peças e serviços só são executados mediante "
    "aprovação prévia do orçamento. A Porto Tec não se responsabiliza por "
    "defeitos pré-existentes não relacionados ao serviço solicitado, nem por "
    "dados armazenados no equipamento."
)

# Tipo de OS: pedido de 2026-08-26. Cada tipo imprime um termo diferente —
# a mesma folha de OS serve pra garantia, venda, retirada, cancelamento etc.,
# e cada situação tem uma responsabilidade jurídica distinta. Lista fechada
# pelo mesmo motivo de sempre (status, setor): dropdown, não campo livre.
TIPOS_OS = [
    "garantia_3_meses",
    "entrada_oficina",
    "saida_oficina",
    "garantia_6_meses",
    "garantia_1_ano",
    "retirada_pre_aprovada",
    "vendas",
    "retirada_aprovada",
    "retirada_orcamento",
    "acionamento_garantia_interno",
    "acionamento_garantia_externo",
    "avaliacao_tecnica",
    "cancelamento",
    "pagamento_faturamento",
    "higienizacao",
    "retirado_aprovado",
]

TIPOS_OS_ROTULO = {
    "garantia_3_meses": "Garantia 3 meses",
    "entrada_oficina": "OS de entrada na oficina",
    "saida_oficina": "OS de saída da oficina",
    "garantia_6_meses": "OS garantia 6 meses",
    "garantia_1_ano": "OS garantia 1 ano",
    "retirada_pre_aprovada": "OS de retirada pré-aprovada",
    "vendas": "OS de vendas",
    "retirada_aprovada": "OS retirada aprovada",
    "retirada_orcamento": "OS de retirada para orçamento",
    "acionamento_garantia_interno": "Acionamento de garantia interno",
    "acionamento_garantia_externo": "Acionamento de garantia externo",
    "avaliacao_tecnica": "Avaliação técnica",
    "cancelamento": "Cancelamento",
    "pagamento_faturamento": "Pagamento / Faturamento",
    "higienizacao": "Higienização",
    "retirado_aprovado": "Retirado / Aprovado",
}

# Termo específico de cada tipo — PENDENTE. O Kalebe vai mandar o texto de
# cada um; até lá, cai no termo genérico (TERMOS_PADRAO) pra impressão nunca
# sair em branco. Trocar aqui, tipo por tipo, quando os textos chegarem —
# não precisa mexer em mais nada (obter()/imprimir_os() já leem daqui).
TERMOS_POR_TIPO = {chave: TERMOS_PADRAO for chave in TIPOS_OS}


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _quem() -> str:
    return session.get("usuario_nome") or "Administrador"


def _campos_os(d: dict) -> dict:
    return {
        "tipo_aparelho": (d.get("tipo_aparelho") or "").strip(),
        "marca": (d.get("marca") or "").strip(),
        "modelo": (d.get("modelo") or "").strip(),
        "numero_serie": (d.get("numero_serie") or "").strip(),
        "acessorios": (d.get("acessorios") or "").strip(),
        "defeito_declarado": (d.get("defeito_declarado") or "").strip(),
        "observacao": (d.get("observacao") or "").strip(),
    }


def _validar_tipo_os(valor):
    """Devolve (mensagem_de_erro, tipo). Erro vazio significa que passou —
    mesmo padrão de _validar_setor em routes/servicos.py."""
    tipo = (valor or "").strip()
    if not tipo:
        return "Escolha o tipo de OS.", None
    if tipo not in TIPOS_OS:
        return "Tipo de OS inválido.", None
    return "", tipo


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@ordens_servico_bp.route("/ordens-servico/metricas", methods=["GET"])
def metricas():
    """OS por mês (últimos 6), tempo médio até finalizar, e indicação que
    mais traz cliente — calculado em Python pra não depender de função de
    data que diverge entre SQLite e Postgres."""
    with db_conn() as conn:
        ordens = fetch_all(conn, "SELECT criado_em, finalizada_em, status FROM ordens_servico")
        indicacoes = fetch_all(conn, """
            SELECT c.indicacao FROM clientes c
             WHERE c.indicacao IS NOT NULL AND c.indicacao <> ''
               AND EXISTS (SELECT 1 FROM ordens_servico os WHERE os.cliente_id = c.id)
        """)

    por_mes = {}
    for o in ordens:
        mes = (o.get("criado_em") or "")[:7]  # "AAAA-MM"
        if mes:
            por_mes[mes] = por_mes.get(mes, 0) + 1
    meses_ordenados = sorted(por_mes.keys())[-6:]

    duracoes = []
    for o in ordens:
        if o.get("finalizada_em") and o.get("criado_em"):
            inicio = _parse_data_hora(o["criado_em"])
            fim = _parse_data_hora(o["finalizada_em"])
            if inicio and fim and fim >= inicio:
                duracoes.append((fim - inicio).total_seconds() / 86400)
    tempo_medio_dias = round(sum(duracoes) / len(duracoes), 1) if duracoes else None

    contagem_indicacao = {}
    for i in indicacoes:
        chave = i["indicacao"]
        contagem_indicacao[chave] = contagem_indicacao.get(chave, 0) + 1
    por_indicacao = sorted(contagem_indicacao.items(), key=lambda x: -x[1])

    return jsonify({
        "por_mes": [{"mes": m, "total": por_mes[m]} for m in meses_ordenados],
        "tempo_medio_dias": tempo_medio_dias,
        "os_finalizadas_com_tempo": len(duracoes),
        "por_indicacao": [{"indicacao": k, "total": v} for k, v in por_indicacao],
        "total_geral": len(ordens),
    })


def _parse_data_hora(texto):
    texto = str(texto or "").strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


@ordens_servico_bp.route("/ordens-servico/status", methods=["GET"])
def listar_status():
    return jsonify({"status": STATUS_OS})


@ordens_servico_bp.route("/ordens-servico/tipos", methods=["GET"])
def listar_tipos():
    return jsonify({"tipos": [{"chave": t, "rotulo": TIPOS_OS_ROTULO[t]} for t in TIPOS_OS]})


@ordens_servico_bp.route("/ordens-servico", methods=["GET"])
def listar():
    """?status filtra; ?cliente_id filtra por cliente; ?busca acha por número
    da OS ou nome do cliente — telefone toca e alguém pergunta "cadê a OS 12",
    não dá pra obrigar a procurar folheando por status. ?dias=N filtra pelas
    abertas nos últimos N dias — mesma convenção de /desfechos e /historico.

    ?fonte=peca|reagendamento separa a fila de Agendar Clientes em dois lados,
    do jeito que o Verificador de CEP já separa em abas: 'peca' é toda OS
    referenciada por pecas_chegada.ordem_servico_id (peça chegou, aba Peças
    mandou pra cá); 'reagendamento' é o resto (OS nova nunca agendada, ou
    técnico marcou volto_depois/reagendar em campo). Sem coluna nova — o
    próprio pecas_chegada já é a marca de qual lado é qual.
    """
    status = (request.args.get("status") or "").strip()
    cliente_id = request.args.get("cliente_id")
    busca = (request.args.get("busca") or "").strip().lower()
    dias = request.args.get("dias")
    fonte = (request.args.get("fonte") or "").strip().lower()

    condicoes, params = [], []
    if status:
        condicoes.append("os.status = ?")
        params.append(status)
    if cliente_id:
        condicoes.append("os.cliente_id = ?")
        params.append(cliente_id)
    if dias and str(dias).isdigit() and 1 <= int(dias) <= 3650:
        corte = (datetime.now(timezone.utc) - timedelta(days=int(dias))).strftime("%Y-%m-%d %H:%M:%S")
        condicoes.append("os.criado_em >= ?")
        params.append(corte)
    if fonte == "peca":
        condicoes.append("EXISTS (SELECT 1 FROM pecas_chegada pc WHERE pc.ordem_servico_id = os.id)")
    elif fonte == "reagendamento":
        condicoes.append("NOT EXISTS (SELECT 1 FROM pecas_chegada pc WHERE pc.ordem_servico_id = os.id)")
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""

    with db_conn() as conn:
        ordens = fetch_all(conn, f"""
            SELECT os.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone
              FROM ordens_servico os
              JOIN clientes c ON c.id = os.cliente_id
              {where}
             ORDER BY os.id DESC
        """, tuple(params))

        contagem = {s: 0 for s in STATUS_OS}
        todas_status = fetch_all(conn, "SELECT status FROM ordens_servico")
        for l in todas_status:
            if l["status"] in contagem:
                contagem[l["status"]] += 1

    if busca:
        numero = busca.lstrip("#").lstrip("0") or "0"
        ordens = [
            o for o in ordens
            if busca in (o.get("cliente_nome") or "").lower()
            or (numero.isdigit() and str(o["id"]) == numero)
        ]

    return jsonify({"ordens": ordens, "contagem": contagem, "total": len(ordens)})


@ordens_servico_bp.route("/ordens-servico/exportar", methods=["GET"])
def exportar():
    """Mesmos filtros de listar() (status/dias/busca), em .xlsx — pra
    contabilidade ou reunião, sem precisar copiar linha por linha da tela."""
    status = (request.args.get("status") or "").strip()
    busca = (request.args.get("busca") or "").strip().lower()
    dias = request.args.get("dias")

    condicoes, params = [], []
    if status:
        condicoes.append("os.status = ?")
        params.append(status)
    if dias and str(dias).isdigit() and 1 <= int(dias) <= 3650:
        corte = (datetime.now(timezone.utc) - timedelta(days=int(dias))).strftime("%Y-%m-%d %H:%M:%S")
        condicoes.append("os.criado_em >= ?")
        params.append(corte)
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""

    with db_conn() as conn:
        ordens = fetch_all(conn, f"""
            SELECT os.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   c.cpf_cnpj AS cliente_cpf_cnpj,
                   t.nome AS tecnico_nome, f.data_referencia, f.dia_semana
              FROM ordens_servico os
              JOIN clientes c ON c.id = os.cliente_id
              LEFT JOIN servicos sv ON sv.id = (
                  SELECT s2.id FROM servicos s2
                   WHERE s2.ordem_servico_id = os.id ORDER BY s2.id DESC LIMIT 1
              )
              LEFT JOIN fichas f ON f.id = sv.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
              {where}
             ORDER BY os.id DESC
        """, tuple(params))

    if busca:
        numero = busca.lstrip("#").lstrip("0") or "0"
        ordens = [
            o for o in ordens
            if busca in (o.get("cliente_nome") or "").lower()
            or (numero.isdigit() and str(o["id"]) == numero)
        ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Ordens de Serviço"

    cabecalho = ["Nº OS", "Status", "Cliente", "CPF/CNPJ", "Telefone",
                "Aparelho", "Marca", "Modelo", "Defeito declarado",
                "Taxa de avaliação", "Atendente", "Técnico", "Dia agendado",
                "Aberta em", "Finalizada em"]
    ws.append(cabecalho)
    for celula in ws[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill(start_color="1A6FD4", end_color="1A6FD4", fill_type="solid")

    for o in ordens:
        dia_agendado = o.get("data_referencia") or o.get("dia_semana") or ""
        ws.append([
            f"OS #{o['id']:06d}", (o["status"] or "").replace("_", " "),
            o.get("cliente_nome") or "", o.get("cliente_cpf_cnpj") or "",
            o.get("cliente_telefone") or "", o.get("tipo_aparelho") or "",
            o.get("marca") or "", o.get("modelo") or "",
            o.get("defeito_declarado") or "", round(o.get("taxa_avaliacao") or 0, 2),
            o.get("atendente") or "", o.get("tecnico_nome") or "", dia_agendado,
            (o.get("criado_em") or "")[:16], (o.get("finalizada_em") or "")[:16],
        ])

    for i, largura in enumerate([11, 20, 22, 16, 15, 14, 12, 14, 30, 12, 14, 14, 13, 16, 16], start=1):
        ws.column_dimensions[chr(64 + i)].width = largura

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nome_arquivo = f"ordens-servico-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(
        buffer, as_attachment=True, download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _pecas_da_os(conn, os_id) -> list:
    """Peças cuja saída de estoque foi vinculada a esta OS — reaproveita
    origem/referencia de estoque_movimentos em vez de criar tabela nova,
    mesmo padrão já usado pra baixa por atendimento."""
    return fetch_all(conn, """
        SELECT m.id, m.quantidade, m.custo_unit, m.criado_em, m.autor,
               e.codigo, e.descricao
          FROM estoque_movimentos m
          JOIN estoque_itens e ON e.id = m.item_id
         WHERE m.origem = 'ordem_servico' AND m.referencia = ? AND m.tipo = 'saida'
         ORDER BY m.id DESC
    """, (str(os_id),))


@ordens_servico_bp.route("/ordens-servico/<int:os_id>/pecas", methods=["GET"])
def listar_pecas(os_id):
    with db_conn() as conn:
        return jsonify({"pecas": _pecas_da_os(conn, os_id)})


@ordens_servico_bp.route("/ordens-servico/<int:os_id>/pecas", methods=["POST"])
def adicionar_peca(os_id):
    """Dá saída de uma peça do estoque vinculada a esta OS. Pode ser chamado
    quantas vezes for preciso — um conserto raramente usa uma peça só."""
    d = request.get_json(silent=True) or {}
    codigo = (d.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"erro": "Informe o código da peça"}), 400

    with db_conn(commit=True) as conn:
        existe = fetch_one(conn, "SELECT id FROM ordens_servico WHERE id = ?", (os_id,))
        if not existe:
            return jsonify({"erro": "Ordem de serviço não encontrada"}), 404

        try:
            resultado = dar_saida(conn, codigo, d.get("quantidade") or 1,
                                  origem="ordem_servico", referencia=str(os_id),
                                  obs=d.get("obs"))
        except (ValueError, TypeError) as exc:
            return jsonify({"erro": str(exc)}), 400

    return jsonify({"mensagem": "Peça baixada do estoque e vinculada à OS", **resultado}), 201


@ordens_servico_bp.route("/ordens-servico/<int:os_id>", methods=["GET"])
def obter(os_id):
    with db_conn() as conn:
        os_row = fetch_one(conn, """
            SELECT os.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   c.email AS cliente_email, c.cpf_cnpj AS cliente_cpf_cnpj,
                   c.endereco AS cliente_endereco, c.numero AS cliente_numero,
                   c.complemento AS cliente_complemento, c.bairro AS cliente_bairro,
                   c.cidade AS cliente_cidade, c.estado AS cliente_estado,
                   c.cep AS cliente_cep
              FROM ordens_servico os
              JOIN clientes c ON c.id = os.cliente_id
             WHERE os.id = ?
        """, (os_id,))
        if not os_row:
            return jsonify({"erro": "Ordem de serviço não encontrada"}), 404

        visitas = fetch_all(conn, """
            SELECT s.id, s.status, s.ordem, f.id AS ficha_id, f.dia_semana,
                   f.data_referencia, t.id AS tecnico_id, t.nome AS tecnico_nome,
                   t.cor AS tecnico_cor, d.desfecho, d.observacao AS desfecho_obs
              FROM servicos s
              JOIN fichas f ON f.id = s.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
              LEFT JOIN servico_desfecho d ON d.servico_id = s.id
             WHERE s.ordem_servico_id = ?
             ORDER BY s.id DESC
        """, (os_id,))

        pecas = _pecas_da_os(conn, os_id)

    termos = TERMOS_POR_TIPO.get(os_row.get("tipo_os"), TERMOS_PADRAO)
    return jsonify({"ordem": os_row, "visitas": visitas, "pecas": pecas, "termos": termos})


@ordens_servico_bp.route("/ordens-servico", methods=["POST"])
def criar():
    """Body: {cliente_id} OU {cliente_novo: {...}} — abrir OS com cliente que
    já existe, ou cadastrar e abrir na mesma tacada (é o caminho mais comum:
    cliente novo ligando pela primeira vez)."""
    d = request.get_json(silent=True) or {}
    campos = _campos_os(d)

    if not campos["tipo_aparelho"] and not campos["defeito_declarado"]:
        return jsonify({"erro": "Informe ao menos o aparelho ou o defeito declarado"}), 400

    erro_tipo_os, tipo_os = _validar_tipo_os(d.get("tipo_os"))
    if erro_tipo_os:
        return jsonify({"erro": erro_tipo_os}), 400

    with db_conn(commit=True) as conn:
        cliente_id = d.get("cliente_id")
        if not cliente_id:
            cliente_novo = d.get("cliente_novo") or {}
            try:
                cliente_id = criar_cliente(conn, cliente_novo)
            except ValueError as exc:
                return jsonify({"erro": str(exc)}), 400
        else:
            existe = fetch_one(conn, "SELECT id FROM clientes WHERE id = ?", (cliente_id,))
            if not existe:
                return jsonify({"erro": "Cliente não encontrado"}), 404

        agora = _agora()
        os_id = insert_returning_id(conn, """
            INSERT INTO ordens_servico
                (cliente_id, atendente, tipo_aparelho, marca, modelo,
                 numero_serie, acessorios, defeito_declarado, taxa_avaliacao,
                 status, observacao, criado_em, criado_por, tipo_os)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, _quem(), campos["tipo_aparelho"], campos["marca"],
              campos["modelo"], campos["numero_serie"], campos["acessorios"],
              campos["defeito_declarado"], _num(d.get("taxa_avaliacao")),
              "aguardando_agendamento", campos["observacao"], agora, _quem(),
              tipo_os))

    return jsonify({"mensagem": "Ordem de serviço aberta", "id": os_id,
                    "cliente_id": cliente_id}), 201


@ordens_servico_bp.route("/ordens-servico/<int:os_id>", methods=["PUT"])
def editar(os_id):
    d = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        existe = fetch_one(conn, "SELECT id FROM ordens_servico WHERE id = ?", (os_id,))
        if not existe:
            return jsonify({"erro": "Ordem de serviço não encontrada"}), 404

        campos, valores = [], []
        for chave in ("tipo_aparelho", "marca", "modelo", "numero_serie",
                     "acessorios", "defeito_declarado", "observacao"):
            if chave in d:
                campos.append(f"{chave} = ?")
                valores.append((d.get(chave) or "").strip())
        if "taxa_avaliacao" in d:
            campos.append("taxa_avaliacao = ?")
            valores.append(_num(d.get("taxa_avaliacao")))
        if "status" in d:
            status = (d.get("status") or "").strip()
            if status not in STATUS_OS:
                return jsonify({"erro": f"Status inválido. Use um de: {', '.join(STATUS_OS)}"}), 400
            campos.append("status = ?")
            valores.append(status)
            if status == "finalizada":
                campos.append("finalizada_em = ?")
                valores.append(_agora())
        if "tipo_os" in d:
            erro_tipo_os, tipo_os = _validar_tipo_os(d.get("tipo_os"))
            if erro_tipo_os:
                return jsonify({"erro": erro_tipo_os}), 400
            campos.append("tipo_os = ?")
            valores.append(tipo_os)

        if not campos:
            return jsonify({"mensagem": "Nada para mudar"})

        campos.append("atualizado_em = ?")
        valores.append(_agora())
        valores.append(os_id)
        execute(conn, f"UPDATE ordens_servico SET {', '.join(campos)} WHERE id = ?", valores)

    return jsonify({"mensagem": "Ordem de serviço atualizada"})


@ordens_servico_bp.route("/ordens-servico/<int:os_id>/agendar", methods=["POST"])
def agendar(os_id):
    """Cria (ou reaproveita) uma visita na agenda do técnico escolhido.

    Body: {tecnico_id, ficha_id} pra um dia que já existe, ou
    {tecnico_id, nova_data} pra abrir um dia novo — mesmo mecanismo do
    reagendamento em tecnico_api.py, só que aqui quem escolhe o técnico é
    quem está abrindo a OS, não o próprio técnico.
    """
    d = request.get_json(silent=True) or {}
    try:
        tecnico_id = int(d.get("tecnico_id"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Escolha o técnico"}), 400

    with db_conn(commit=True) as conn:
        os_row = fetch_one(conn, """
            SELECT os.*, c.nome AS cliente_nome, c.cep AS cliente_cep,
                   c.endereco AS cliente_endereco, c.numero AS cliente_numero,
                   c.bairro AS cliente_bairro, c.cidade AS cliente_cidade
              FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
             WHERE os.id = ?
        """, (os_id,))
        if not os_row:
            return jsonify({"erro": "Ordem de serviço não encontrada"}), 404

        tecnico = fetch_one(conn, "SELECT id FROM tecnicos WHERE id = ?", (tecnico_id,))
        if not tecnico:
            return jsonify({"erro": "Técnico não encontrado"}), 404

        ficha_id = d.get("ficha_id")
        if ficha_id:
            ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ? AND tecnico_id = ?",
                              (ficha_id, tecnico_id))
            if not ficha:
                return jsonify({"erro": "Esse dia não existe ou não é desse técnico"}), 404
        else:
            nova_data = (d.get("nova_data") or "").strip()
            if not nova_data:
                return jsonify({"erro": "Escolha um dia existente ou uma data nova"}), 400
            from routes.fichas import nome_dia_semana
            try:
                dia = nome_dia_semana(nova_data)
            except ValueError:
                return jsonify({"erro": "Data inválida"}), 400

            # Travado contra duas OS sendo agendadas pro mesmo técnico/dia
            # quase ao mesmo tempo criarem ficha duplicada — obter_ou_criar_ficha
            # em routes/fichas.py é o ponto único que resolve isso pros três
            # lugares que precisam de "reaproveita se existe, senão cria".
            ficha_id, _ = obter_ou_criar_ficha(conn, tecnico_id, dia, nova_data)
            ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))

        # Endereço do cliente vira o ponto na rota. Sem CEP não geocodifica,
        # mas a visita ainda entra — corrige depois é melhor que não poder
        # agendar por falta de um dado que a etiqueta às vezes não tem.
        cep = "".join(c for c in (os_row.get("cliente_cep") or "") if c.isdigit())
        geo = geocode_cep(cep, numero=os_row.get("cliente_numero") or "") if cep else None
        endereco_completo = (geo.endereco if geo else " ".join(x for x in [
            os_row.get("cliente_endereco"), os_row.get("cliente_numero"),
            os_row.get("cliente_bairro"), os_row.get("cliente_cidade"),
        ] if x)) or None

        ultima = fetch_one(conn, "SELECT MAX(ordem) AS m FROM servicos WHERE ficha_id = ?",
                           (ficha_id,))
        servico_id = insert_returning_id(conn, """
            INSERT INTO servicos (ficha_id, cep, numero, endereco_completo, lat, lng,
                                  cliente, descricao, ordem, status, tipo_aparelho,
                                  modelo, ordem_servico_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ficha_id, cep, os_row.get("cliente_numero") or "", endereco_completo,
              geo.lat if geo else None, geo.lng if geo else None,
              os_row.get("cliente_nome"), os_row.get("defeito_declarado"),
              ((ultima or {}).get("m") or 0) + 1, "pendente",
              os_row.get("tipo_aparelho"), os_row.get("modelo"), os_id))

        execute(conn, "UPDATE ordens_servico SET status = ?, atualizado_em = ? WHERE id = ?",
               ("agendada", _agora(), os_id))

        recalcular_rota(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Visita agendada", "ficha_id": ficha_id,
                    "servico_id": servico_id}), 201


@ordens_servico_bp.route("/ordens-servico/<int:os_id>/desagendar/<int:servico_id>", methods=["DELETE"])
def desagendar(os_id, servico_id):
    """Desfaz um agendamento feito com técnico/dia errado.

    Só mexe em visita ainda PENDENTE — uma já concluída tem desfecho e
    histórico reais, desagendar isso apagaria trabalho que aconteceu de
    verdade. A visita errada é removida (nunca chegou a acontecer, não há o
    que preservar); se não sobrar nenhuma outra visita pendente ou
    concluída, a OS volta pra 'aguardando_agendamento'.
    """
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, """
            SELECT * FROM servicos WHERE id = ? AND ordem_servico_id = ?
        """, (servico_id, os_id))
        if not servico:
            return jsonify({"erro": "Visita não encontrada nesta OS"}), 404
        if servico["status"] != "pendente":
            return jsonify({"erro": "Só dá pra desagendar uma visita que ainda não aconteceu"}), 400

        ficha_id = servico["ficha_id"]
        execute(conn, "DELETE FROM servicos WHERE id = ?", (servico_id,))

        restantes = fetch_one(conn, """
            SELECT COUNT(*) AS total FROM servicos WHERE ordem_servico_id = ?
        """, (os_id,))["total"]
        if not restantes:
            execute(conn, "UPDATE ordens_servico SET status = ?, atualizado_em = ? WHERE id = ?",
                   ("aguardando_agendamento", _agora(), os_id))

        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if ficha:
            recalcular_rota(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Visita desagendada"})
