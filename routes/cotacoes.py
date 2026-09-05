"""Lista de peças aguardando cotação de preço.

Fica ANTES da compra: o técnico fotografa a etiqueta em campo (desfecho
"Cotação de peça") ou alguém no escritório lança à mão — por código ou só
pelo modelo da máquina — e o item entra aqui até alguém confirmar o valor
com o fornecedor. Depois de cotado, o valor fica registrado; a compra em si
continua acontecendo por fora (planilha / rotas/pedidos.py), esta tabela não
lança pedido nenhum.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id

cotacoes_bp = Blueprint("cotacoes", __name__)

# Mesmo teto e mesma validação de routes/tecnico_api.py (_gravar_foto): o
# navegador já reduz a foto para 1280px de lado maior em JPEG antes de
# mandar (reduzirFotoInteira em app.js), então 900 KB em base64 é folga
# larga sem virar porta pra despejarem arquivo grande no banco. Duplicado
# em vez de importado — mesmo motivo do _SETOR_ATIVO espalhado pelas rotas:
# são dois pontos de entrada (o técnico em campo, o admin na hora de
# cadastrar a peça) que não têm por que depender um do outro.
FOTO_MAXIMA = 900 * 1024
PREFIXOS_FOTO = ("data:image/jpeg;base64,", "data:image/png;base64,",
                 "data:image/webp;base64,")


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _autor() -> str:
    return session.get("usuario_nome") or "Administrador"


def _foto_valida(foto) -> str:
    """Devolve a foto se passar na validação, senão None — silencioso de
    propósito (mesma regra de _gravar_foto): uma foto recusada não pode
    quebrar o resto do cadastro, só entra sem ela."""
    if not isinstance(foto, str) or not foto.startswith(PREFIXOS_FOTO):
        return None
    if len(foto) > FOTO_MAXIMA:
        return None
    return foto


@cotacoes_bp.route("/cotacoes", methods=["GET"])
def listar():
    """?status=pendente|cotado filtra; sem parâmetro, traz tudo (mais recente primeiro)."""
    status = (request.args.get("status") or "").strip()
    with db_conn() as conn:
        if status:
            itens = fetch_all(conn, """
                SELECT * FROM cotacoes WHERE status = ? ORDER BY id DESC
            """, (status,))
        else:
            itens = fetch_all(conn, "SELECT * FROM cotacoes ORDER BY id DESC")
    return jsonify({
        "itens": itens,
        "pendentes": sum(1 for i in itens if i["status"] == "pendente"),
    })


@cotacoes_bp.route("/cotacoes/comparar", methods=["GET"])
def comparar_fornecedores():
    """Comparador de preço entre fornecedores pra um código (pedido de
    2026-09-02/03: "não só Panasonic").

    Não é cadastro de fornecedor novo nem cotação simultânea de verdade —
    aproveita o que a fila de Cotação JÁ acumula com o tempo: toda vez que
    alguém marca `valor_cotado` + `fornecedor` aqui (rota PUT acima), a linha
    fica gravada com `status='cotado'` (não é apagada — só o atalho de
    "Cotação de peça" indo direto pro orçamento apaga a dele, um caso à
    parte). Juntando isso por código, dá pra ver "da última vez, a Casa X
    cobrou R$40 e a Y cobrou R$55" sem ter cadastrado fornecedor nenhum antes.

    Um fornecedor pode aparecer mais de uma vez cotado ao longo do tempo —
    fica só o mais RECENTE dele (preço antigo não ajuda a decidir hoje).
    """
    codigo = (request.args.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"erro": "Informe o código da peça"}), 400

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT fornecedor, valor_cotado, criado_em, atualizado_em
              FROM cotacoes
             WHERE LOWER(codigo) = LOWER(?) AND valor_cotado IS NOT NULL
                   AND fornecedor IS NOT NULL AND fornecedor <> ''
             ORDER BY id DESC
        """, (codigo,))

    mais_recente_por_fornecedor = {}
    for l in linhas:
        chave = l["fornecedor"].strip().lower()
        if chave not in mais_recente_por_fornecedor:
            mais_recente_por_fornecedor[chave] = l

    resultado = sorted(mais_recente_por_fornecedor.values(),
                       key=lambda l: l["valor_cotado"])
    return jsonify({"codigo": codigo, "fornecedores": resultado})


@cotacoes_bp.route("/cotacoes", methods=["POST"])
def criar():
    d = request.get_json(silent=True) or {}
    codigo = (d.get("codigo") or "").strip()
    modelo = (d.get("modelo") or "").strip()
    descricao = (d.get("descricao") or "").strip()
    if not codigo and not modelo:
        return jsonify({"erro": "Informe ao menos o código da peça ou o modelo da máquina"}), 400

    try:
        quantidade = max(1.0, float(d.get("quantidade") or 1))
    except (TypeError, ValueError):
        quantidade = 1.0

    foto = _foto_valida(d.get("foto"))

    with db_conn(commit=True) as conn:
        novo_id = insert_returning_id(conn, """
            INSERT INTO cotacoes (codigo, modelo, descricao, quantidade, criado_em, criado_por, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (codigo, modelo, descricao, quantidade, _agora(), _autor(), foto))

    return jsonify({"mensagem": "Item adicionado à lista de cotação", "id": novo_id}), 201


def _aviso_alta_preco(conn, codigo, novo_valor, excluir_id=None):
    """Alerta de alta de preço (pedido de 2026-09-02/03: "quando o preço de
    uma peça sobe mais de X% desde a última compra") — compara com o último
    valor_cotado registrado pra ESTE código, de qualquer fornecedor. Chamado
    ANTES de gravar o novo valor, óbvio, senão "o último" seria o que está
    prestes a virar agora mesmo. `excluir_id` tira a própria linha da
    comparação quando ela já existe em `cotacoes` (edição); None quando o
    valor está sendo confirmado por fora dessa tabela (ver cotacao-confirmar).
    """
    codigo = (codigo or "").strip()
    if not codigo or not novo_valor:
        return None
    anterior = fetch_one(conn, """
        SELECT valor_cotado FROM cotacoes
         WHERE LOWER(codigo) = LOWER(?) AND valor_cotado IS NOT NULL
               AND (? IS NULL OR id <> ?)
         ORDER BY id DESC LIMIT 1
    """, (codigo, excluir_id, excluir_id))
    if not anterior or not anterior.get("valor_cotado"):
        return None
    valor_antigo = float(anterior["valor_cotado"])
    if valor_antigo <= 0:
        return None
    variacao = (novo_valor - valor_antigo) / valor_antigo
    if variacao < 0.20:   # 20% pra cima já vale avisar
        return None
    return {"valor_anterior": valor_antigo, "valor_novo": novo_valor,
            "variacao_pct": round(variacao * 100, 1)}


@cotacoes_bp.route("/cotacoes/<int:item_id>", methods=["PUT"])
def atualizar(item_id):
    """Edita campos e/ou marca como cotado (valor_cotado + fornecedor)."""
    d = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        item = fetch_one(conn, "SELECT id, codigo FROM cotacoes WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404

        aviso_alta = None
        codigo_atual = (d.get("codigo") or item.get("codigo") or "").strip()
        if "valor_cotado" in d and d.get("valor_cotado") not in (None, "") and codigo_atual:
            try:
                novo_valor = float(d["valor_cotado"])
            except (TypeError, ValueError):
                novo_valor = None
            aviso_alta = _aviso_alta_preco(conn, codigo_atual, novo_valor, excluir_id=item_id)

        campos, valores = [], []
        if "codigo" in d:
            campos.append("codigo = ?"); valores.append((d.get("codigo") or "").strip())
        if "modelo" in d:
            campos.append("modelo = ?"); valores.append((d.get("modelo") or "").strip())
        if "descricao" in d:
            campos.append("descricao = ?"); valores.append((d.get("descricao") or "").strip())
        if "quantidade" in d:
            try:
                campos.append("quantidade = ?"); valores.append(max(1.0, float(d["quantidade"])))
            except (TypeError, ValueError):
                return jsonify({"erro": "Quantidade inválida"}), 400
        if "valor_cotado" in d:
            valor = d.get("valor_cotado")
            campos.append("valor_cotado = ?")
            valores.append(None if valor in (None, "") else float(valor))
        if "fornecedor" in d:
            campos.append("fornecedor = ?"); valores.append((d.get("fornecedor") or "").strip())
        if "foto" in d:
            campos.append("foto = ?"); valores.append(_foto_valida(d.get("foto")))
        if "status" in d:
            status = (d.get("status") or "").strip()
            if status not in ("pendente", "cotado"):
                return jsonify({"erro": "Status inválido. Use 'pendente' ou 'cotado'"}), 400
            campos.append("status = ?"); valores.append(status)

        if not campos:
            return jsonify({"mensagem": "Nada para mudar"})

        campos.append("atualizado_em = ?"); valores.append(_agora())
        valores.append(item_id)
        execute(conn, f"UPDATE cotacoes SET {', '.join(campos)} WHERE id = ?", valores)

    resposta = {"mensagem": "Item atualizado"}
    if aviso_alta:
        resposta["aviso_alta"] = aviso_alta
    return jsonify(resposta)


@cotacoes_bp.route("/cotacoes/<int:item_id>", methods=["DELETE"])
def remover(item_id):
    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM cotacoes WHERE id = ?", (item_id,))
    if not apagados:
        return jsonify({"erro": "Item não encontrado"}), 404
    return jsonify({"mensagem": "Item removido"})


def _os_orcamento_do_cliente(conn, servico, quem):
    """Acha (se o atendimento já tem OS) ou cria a OS-orçamento do cliente
    deste atendimento, pra pendurar um item de cotação confirmada. Mesma
    lógica de identificar cliente de
    routes/tecnico_api.py:_criar_os_orcamento_do_tecnico, só que chamada
    pelo ESCRITÓRIO confirmando o preço, não pelo técnico em campo (por
    isso sem assinatura/foto aqui — quem colheria isso é o técnico, que já
    foi embora a essa altura)."""
    if servico.get("ordem_servico_id"):
        os_id = servico["ordem_servico_id"]
        execute(conn, """
            UPDATE ordens_servico SET modelo_os = 'orcamento', status = 'aguardando_orcamento'
             WHERE id = ? AND modelo_os != 'orcamento'
        """, (os_id,))
        return os_id

    cliente_nome = (servico.get("cliente") or "").strip()
    if not cliente_nome:
        return None

    from routes.clientes import criar_cliente
    existente = fetch_one(conn, "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)", (cliente_nome,))
    if existente:
        cliente_id = existente["id"]
    else:
        try:
            cliente_id = criar_cliente(conn, {"nome": cliente_nome, "telefone": servico.get("telefone") or ""})
        except ValueError:
            return None

    import secrets
    agora = _agora()
    token_cliente = secrets.token_urlsafe(24)
    os_id = insert_returning_id(conn, """
        INSERT INTO ordens_servico
            (cliente_id, atendente, tipo_aparelho, modelo, taxa_avaliacao,
             status, modelo_os, criado_em, criado_por, token_cliente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente_id, quem, servico.get("tipo_aparelho") or "", servico.get("modelo") or "", 0,
          "aguardando_orcamento", "orcamento", agora, quem, token_cliente))
    execute(conn, "UPDATE servicos SET ordem_servico_id = ? WHERE id = ?", (os_id, servico["id"]))
    return os_id


@cotacoes_bp.route("/desfechos/<int:servico_id>/cotacao-confirmar", methods=["POST"])
def confirmar_cotacao_desfecho(servico_id):
    """Pedido de 2026-09-01: confirma o preço encontrado numa "casa de
    peças" pra uma Cotação de Peça que veio de atendimento de técnico — a
    peça vira um ITEM de verdade na OS de orçamento do cliente (cria a OS
    se ele não tiver uma ainda), e o item de cotação SOME da fila — o
    trabalho dele acabou, virou orçamento."""
    d = request.get_json(silent=True) or {}
    try:
        valor = float(d.get("valor"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe o valor cotado"}), 400
    if valor <= 0:
        return jsonify({"erro": "O valor tem que ser maior que zero"}), 400
    fornecedor = (d.get("fornecedor") or "").strip()

    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Atendimento não encontrado"}), 404
        # A trava é a linha em `cotacoes` (a fila de verdade), não
        # `servico_desfecho` — esse fica intacto de propósito como histórico
        # do atendimento, então checá-lo deixaria confirmar a MESMA cotação
        # várias vezes, duplicando o item no orçamento a cada clique.
        cotacao = fetch_one(conn, "SELECT id, codigo FROM cotacoes WHERE servico_id = ?", (servico_id,))
        if not cotacao:
            return jsonify({"erro": "Essa cotação já foi confirmada ou não existe mais"}), 404
        desfecho = fetch_one(conn, """
            SELECT * FROM servico_desfecho WHERE servico_id = ? AND desfecho = 'cotacao_peca'
        """, (servico_id,)) or {}

        # Mesmo alerta de alta de preço da confirmação pela aba Peças (ver
        # marcarCotado/atualizar acima) — confirmar por aqui não pode ficar
        # cego a isso só porque veio de um atendimento de técnico.
        aviso_alta = _aviso_alta_preco(conn, cotacao.get("codigo"), valor, excluir_id=cotacao["id"])

        os_id = _os_orcamento_do_cliente(conn, servico, _autor())
        if not os_id:
            return jsonify({"erro": "Não consegui identificar o cliente desse atendimento pra montar a OS"}), 400

        nome_item = desfecho.get("peca") or "Peça cotada"
        if fornecedor:
            nome_item = f"{nome_item} ({fornecedor})"
        execute(conn, """
            INSERT INTO ordem_servico_itens (ordem_servico_id, nome, valor, criado_em)
            VALUES (?, ?, ?, ?)
        """, (os_id, nome_item, valor, _agora()))

        # Some da fila de cotação — o trabalho dela virou item de orçamento.
        execute(conn, "DELETE FROM cotacoes WHERE servico_id = ?", (servico_id,))

    resposta = {"mensagem": "Cotação confirmada e enviada pro orçamento", "os_id": os_id}
    if aviso_alta:
        resposta["aviso_alta"] = aviso_alta
    return jsonify(resposta)
