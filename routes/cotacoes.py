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


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _autor() -> str:
    return session.get("usuario_nome") or "Administrador"


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

    with db_conn(commit=True) as conn:
        novo_id = insert_returning_id(conn, """
            INSERT INTO cotacoes (codigo, modelo, descricao, quantidade, criado_em, criado_por)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (codigo, modelo, descricao, quantidade, _agora(), _autor()))

    return jsonify({"mensagem": "Item adicionado à lista de cotação", "id": novo_id}), 201


@cotacoes_bp.route("/cotacoes/<int:item_id>", methods=["PUT"])
def atualizar(item_id):
    """Edita campos e/ou marca como cotado (valor_cotado + fornecedor)."""
    d = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        item = fetch_one(conn, "SELECT id FROM cotacoes WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404

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

    return jsonify({"mensagem": "Item atualizado"})


@cotacoes_bp.route("/cotacoes/<int:item_id>", methods=["DELETE"])
def remover(item_id):
    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM cotacoes WHERE id = ?", (item_id,))
    if not apagados:
        return jsonify({"erro": "Item não encontrado"}), 404
    return jsonify({"mensagem": "Item removido"})
