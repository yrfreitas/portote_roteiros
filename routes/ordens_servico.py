"""Ordem de Serviço — o documento do atendimento, próprio do site.

Decisão de 2026-08-21: não depende do AgoraOS. A OS é o registro persistente
(cliente, equipamento, defeito, status); QUEM vai atender e QUANDO continuam
sendo respondidos pelo sistema de fichas/técnicos que já existe — a OS só se
liga a um `servico` (routes/servicos.py) em vez de duplicar agenda. Uma OS
pode ter mais de uma visita ligada a ela com o tempo (voltou pra buscar
peça), por isso o vínculo mora em servicos.ordem_servico_id.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

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


@ordens_servico_bp.route("/ordens-servico", methods=["GET"])
def listar():
    """?status filtra; ?cliente_id filtra por cliente; ?busca acha por número
    da OS ou nome do cliente — telefone toca e alguém pergunta "cadê a OS 12",
    não dá pra obrigar a procurar folheando por status."""
    status = (request.args.get("status") or "").strip()
    cliente_id = request.args.get("cliente_id")
    busca = (request.args.get("busca") or "").strip().lower()

    condicoes, params = [], []
    if status:
        condicoes.append("os.status = ?")
        params.append(status)
    if cliente_id:
        condicoes.append("os.cliente_id = ?")
        params.append(cliente_id)
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

    return jsonify({"ordem": os_row, "visitas": visitas, "pecas": pecas, "termos": TERMOS_PADRAO})


@ordens_servico_bp.route("/ordens-servico", methods=["POST"])
def criar():
    """Body: {cliente_id} OU {cliente_novo: {...}} — abrir OS com cliente que
    já existe, ou cadastrar e abrir na mesma tacada (é o caminho mais comum:
    cliente novo ligando pela primeira vez)."""
    d = request.get_json(silent=True) or {}
    campos = _campos_os(d)

    if not campos["tipo_aparelho"] and not campos["defeito_declarado"]:
        return jsonify({"erro": "Informe ao menos o aparelho ou o defeito declarado"}), 400

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
                 status, observacao, criado_em, criado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, _quem(), campos["tipo_aparelho"], campos["marca"],
              campos["modelo"], campos["numero_serie"], campos["acessorios"],
              campos["defeito_declarado"], _num(d.get("taxa_avaliacao")),
              "aguardando_agendamento", campos["observacao"], agora, _quem()))

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
