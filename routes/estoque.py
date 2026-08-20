"""Estoque de peças — o SITE é o dono do saldo.

POR QUE ISTO EXISTE, e não no AgoraOS:
a API do AgoraOS lê estoque mas não deixa escrever — não liga o controle nem
dá entrada de saldo (testado exaustivamente em 2026-08). Então a "baixa de
peça" que já existe lá dentro nunca reduzia nada. Aqui o saldo é do site:
entra quando a peça é comprada e sai quando é usada.

DUAS REGRAS QUE DEFINEM TUDO:

1. NADA MEXE NO SALDO SEM DEIXAR MOVIMENTO. Toda entrada, saída e ajuste grava
   uma linha em estoque_movimentos com o saldo daquele instante. Um saldo sem
   histórico é impossível de auditar — a pergunta "de onde veio esse número?"
   fica sem resposta, e é a primeira que se faz quando o estoque não bate.

2. CUSTO MÉDIO PONDERADO na entrada. Comprar 2 placas a R$ 300 e depois 3 a
   R$ 400 não dá "R$ 400 cada" nem "R$ 350 na média simples": dá
   (2×300 + 3×400) / 5 = R$ 360. É o número certo para saber quanto vale o
   estoque parado e quanto custou a peça que saiu. A média simples mentiria
   sempre que os preços variassem — e eles variam.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import IS_PG, db_conn, execute, fetch_all, fetch_one, insert_returning_id

log = logging.getLogger("portotec.estoque")

estoque_bp = Blueprint("estoque", __name__)


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _autor():
    return session.get("usuario_nome") or "Administrador"


def _norm_codigo(c):
    return (c or "").strip().upper()


def _registrar_movimento(conn, item_id, tipo, qtd, saldo_apos,
                         custo_unit=None, origem="manual", referencia=None, obs=None):
    execute(conn, """
        INSERT INTO estoque_movimentos
            (item_id, tipo, quantidade, saldo_apos, custo_unit, origem,
             referencia, autor, obs, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, tipo, qtd, saldo_apos, custo_unit, origem, referencia,
          _autor(), obs, _agora()))


def dar_entrada(conn, codigo, descricao, quantidade, custo_unit=0.0,
                origem="manual", referencia=None, obs=None):
    """Entra peça no estoque, recalculando o custo médio ponderado.

    Reaproveitável de fora (é o que a NF-e vai chamar, fase 2), por isso recebe
    a conexão: entra na mesma transação de quem chamou, e não sobra entrada de
    um processo que falhou no meio.
    """
    codigo = _norm_codigo(codigo)
    if not codigo:
        raise ValueError("Código da peça é obrigatório")
    quantidade = float(quantidade)
    if quantidade <= 0:
        raise ValueError("Quantidade tem que ser maior que zero")
    custo_unit = max(0.0, float(custo_unit or 0))

    item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE codigo = ?", (codigo,))

    if item is None:
        novo_id = insert_returning_id(conn, """
            INSERT INTO estoque_itens
                (codigo, descricao, saldo, custo_medio, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (codigo, (descricao or "").strip(), quantidade, custo_unit,
              _agora(), _agora()))
        _registrar_movimento(conn, novo_id, "entrada", quantidade, quantidade,
                             custo_unit, origem, referencia, obs)
        return {"item_id": novo_id, "saldo": quantidade, "custo_medio": custo_unit,
                "criado": True}

    saldo_antigo = float(item["saldo"] or 0)
    custo_antigo = float(item["custo_medio"] or 0)
    saldo_novo = saldo_antigo + quantidade

    # Custo médio ponderado. Só recalcula quando a entrada TEM custo — entrada
    # a custo zero (ex: brinde, ajuste) não pode zerar o custo do que já
    # estava lá, senão o valor do estoque despencaria de graça.
    if custo_unit > 0:
        custo_novo = (saldo_antigo * custo_antigo + quantidade * custo_unit) / saldo_novo
    else:
        custo_novo = custo_antigo

    execute(conn, """
        UPDATE estoque_itens
           SET saldo = ?, custo_medio = ?, atualizado_em = ?,
               descricao = COALESCE(NULLIF(?, ''), descricao)
         WHERE id = ?
    """, (saldo_novo, custo_novo, _agora(), (descricao or "").strip(), item["id"]))
    _registrar_movimento(conn, item["id"], "entrada", quantidade, saldo_novo,
                        custo_unit, origem, referencia, obs)
    return {"item_id": item["id"], "saldo": saldo_novo, "custo_medio": custo_novo,
            "criado": False}


def dar_saida(conn, codigo, quantidade, origem="manual", referencia=None,
              obs=None, permitir_negativo=False):
    """Baixa peça do estoque. Devolve o item ou levanta erro."""
    codigo = _norm_codigo(codigo)
    item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE codigo = ?", (codigo,))
    if item is None:
        raise ValueError(f"Peça {codigo} não existe no estoque")

    quantidade = float(quantidade)
    if quantidade <= 0:
        raise ValueError("Quantidade tem que ser maior que zero")

    saldo_antigo = float(item["saldo"] or 0)
    saldo_novo = saldo_antigo - quantidade
    # Trava contra saldo negativo: baixar mais do que existe quase sempre é
    # erro de digitação. `permitir_negativo` fica para o dia em que a baixa
    # automática precisar registrar consumo mesmo sem entrada lançada.
    if saldo_novo < 0 and not permitir_negativo:
        raise ValueError(
            f"Saldo insuficiente: há {saldo_antigo:g} em estoque e a saída é de {quantidade:g}")

    execute(conn, "UPDATE estoque_itens SET saldo = ?, atualizado_em = ? WHERE id = ?",
            (saldo_novo, _agora(), item["id"]))
    _registrar_movimento(conn, item["id"], "saida", quantidade, saldo_novo,
                        float(item["custo_medio"] or 0), origem, referencia, obs)
    return {"item_id": item["id"], "saldo": saldo_novo}


# ─── API ────────────────────────────────────────────────────────────────
@estoque_bp.route("/estoque", methods=["GET"])
def listar():
    """Todos os itens, com o alerta de mínimo já resolvido. `busca` filtra por
    código ou descrição — o estoque cresce e rolar a lista inteira cansa."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    busca = (request.args.get("busca") or "").strip().lower()

    with db_conn() as conn:
        itens = fetch_all(conn, """
            SELECT e.*, s.nome AS setor_nome, s.cor AS setor_cor
              FROM estoque_itens e
              LEFT JOIN setores s ON s.id = e.setor_id
             ORDER BY e.descricao, e.codigo
        """)

    if busca:
        itens = [i for i in itens
                 if busca in (i.get("codigo") or "").lower()
                 or busca in (i.get("descricao") or "").lower()]

    for i in itens:
        i["abaixo_minimo"] = (float(i.get("minimo") or 0) > 0
                              and float(i.get("saldo") or 0) <= float(i["minimo"]))
        i["valor_total"] = round(float(i.get("saldo") or 0) * float(i.get("custo_medio") or 0), 2)

    return jsonify({
        "itens": itens,
        "total_itens": len(itens),
        "abaixo_minimo": sum(1 for i in itens if i["abaixo_minimo"]),
        "valor_investido": round(sum(i["valor_total"] for i in itens), 2),
    })


@estoque_bp.route("/estoque/entrada", methods=["POST"])
def entrada():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    try:
        with db_conn(commit=True) as conn:
            r = dar_entrada(conn, d.get("codigo"), d.get("descricao"),
                            d.get("quantidade"), d.get("custo_unit"),
                            origem="manual", obs=d.get("obs"))
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Entrada registrada", **r}), 201


@estoque_bp.route("/estoque/saida", methods=["POST"])
def saida():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    try:
        with db_conn(commit=True) as conn:
            r = dar_saida(conn, d.get("codigo"), d.get("quantidade"),
                          origem="manual", obs=d.get("obs"))
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Saída registrada", **r}), 201


@estoque_bp.route("/estoque/<int:item_id>", methods=["PUT"])
def editar_item(item_id):
    """Ajusta mínimo, descrição, setor — e faz o AJUSTE de saldo por inventário.

    Ajuste é diferente de entrada/saída: é a contagem física dizendo qual é a
    verdade. Grava um movimento 'ajuste' com a diferença, para o histórico
    mostrar que o número foi corrigido na mão, e por quanto.
    """
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404

        campos, valores = [], []
        if "minimo" in d:
            campos.append("minimo = ?"); valores.append(max(0.0, float(d["minimo"] or 0)))
        if "descricao" in d:
            campos.append("descricao = ?"); valores.append((d["descricao"] or "").strip())
        if "setor_id" in d:
            campos.append("setor_id = ?"); valores.append(d["setor_id"] or None)

        if campos:
            valores.append(item_id)
            execute(conn, f"UPDATE estoque_itens SET {', '.join(campos)} WHERE id = ?", valores)

        if "saldo_contado" in d and d["saldo_contado"] not in (None, ""):
            contado = float(d["saldo_contado"])
            diferenca = contado - float(item["saldo"] or 0)
            if diferenca != 0:
                execute(conn, "UPDATE estoque_itens SET saldo = ?, atualizado_em = ? WHERE id = ?",
                        (contado, _agora(), item_id))
                _registrar_movimento(conn, item_id, "ajuste", diferenca, contado,
                                    float(item["custo_medio"] or 0), "inventário",
                                    None, d.get("obs") or "Contagem física")

    return jsonify({"mensagem": "Item atualizado"})


@estoque_bp.route("/estoque/<int:item_id>", methods=["DELETE"])
def remover_item(item_id):
    """Remove o item e todo o histórico dele. Só admin, e some de vez —
    quando é peça cadastrada por engano, não uma que acabou (essa fica com
    saldo zero, para o histórico sobreviver)."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM estoque_itens WHERE id = ?", (item_id,))
    if not apagados:
        return jsonify({"erro": "Item não encontrado"}), 404
    return jsonify({"mensagem": "Item removido"})


@estoque_bp.route("/estoque/<int:item_id>/historico", methods=["GET"])
def historico(item_id):
    """Todo movimento do item, mais recente primeiro. É a auditoria do saldo."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn() as conn:
        item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404
        movs = fetch_all(conn, """
            SELECT tipo, quantidade, saldo_apos, custo_unit, origem,
                   referencia, autor, obs, criado_em
              FROM estoque_movimentos WHERE item_id = ?
             ORDER BY id DESC
        """, (item_id,))
    return jsonify({"item": item, "movimentos": movs})
