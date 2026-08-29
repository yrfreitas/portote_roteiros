"""Venda de balcão — pedido de 2026-08-29: bipar código de barras ou
pesquisar o produto (com foto, pra ficar bonito na tela), montar o
carrinho e fechar com os dados do cliente, saindo uma nota de venda
pequena pra imprimir (bem menor que o modelo de impressão da OS).

Uma venda É uma saída de estoque — por isso reaproveita `dar_saida` de
routes/estoque.py (mesmo custo médio, mesmo saldo, mesmo movimento
registrado) em vez de duplicar essa lógica aqui. O que este módulo
acrescenta é só a NOTA em cima: cliente, forma de pagamento, garantia e
os itens vendidos, agrupados numa venda.
"""
import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from routes.estoque import dar_saida

log = logging.getLogger("portotec.vendas")

vendas_bp = Blueprint("vendas", __name__)


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _autor():
    return session.get("usuario_nome") or "Administrador"


@vendas_bp.route("/vendas/produtos", methods=["GET"])
def produtos():
    """Produtos pra vender: só o que faz sentido no balcão (sem custo médio,
    sem mínimo) — endpoint próprio, e não /api/estoque, pra quem só tem a
    permissão 'vendas' poder bipar/pesquisar sem enxergar custo nem precisar
    da permissão de gerenciar estoque."""
    with db_conn() as conn:
        itens = fetch_all(conn, """
            SELECT id, codigo, descricao, marca, aparelho, modelo, foto,
                   saldo, preco_venda
              FROM estoque_itens
             ORDER BY descricao, codigo
        """)
    return jsonify({"itens": itens})


@vendas_bp.route("/vendas", methods=["GET"])
def listar():
    """Vendas recentes, mais nova primeiro — pra reimprimir ou conferir o
    que já saiu hoje. ?dias=N limita o período (padrão 30)."""
    try:
        dias = max(1, min(365, int(request.args.get("dias", 30))))
    except (TypeError, ValueError):
        dias = 30
    limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d 00:00:00")

    with db_conn() as conn:
        vendas = fetch_all(conn, """
            SELECT v.*, (SELECT COUNT(*) FROM venda_itens vi WHERE vi.venda_id = v.id) AS total_itens
              FROM vendas v
             WHERE v.criado_em >= ?
             ORDER BY v.criado_em DESC
        """, (limite,))
    return jsonify({"vendas": vendas})


@vendas_bp.route("/vendas", methods=["POST"])
def criar():
    """Fecha a venda: valida o carrinho INTEIRO antes de escrever qualquer
    coisa (um item sem saldo no meio da lista não pode deixar os anteriores
    já baixados do estoque presos numa venda que não vai existir), grava a
    nota e dá saída de cada item pelo mesmo caminho de estoque/saida."""
    d = request.get_json(silent=True) or {}
    cliente_nome = (d.get("cliente_nome") or "").strip()
    if not cliente_nome:
        return jsonify({"erro": "Informe o nome do cliente"}), 400

    itens_carrinho = d.get("itens") or []
    if not itens_carrinho:
        return jsonify({"erro": "O carrinho está vazio"}), 400

    cliente_telefone = (d.get("cliente_telefone") or "").strip()
    cliente_cpf_cnpj = (d.get("cliente_cpf_cnpj") or "").strip()
    forma_pagamento = (d.get("forma_pagamento") or "").strip()
    garantia_texto = (d.get("garantia_texto") or "").strip()

    try:
        with db_conn(commit=True) as conn:
            linhas = []
            for linha in itens_carrinho:
                item_id = linha.get("item_id")
                try:
                    quantidade = float(linha.get("quantidade") or 0)
                except (TypeError, ValueError):
                    quantidade = 0
                if not item_id or quantidade <= 0:
                    raise ValueError("Item de venda inválido")
                item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE id = ?", (item_id,))
                if not item:
                    raise ValueError(f"Produto (id {item_id}) não encontrado")
                saldo = float(item.get("saldo") or 0)
                if quantidade > saldo:
                    raise ValueError(
                        f"Saldo insuficiente de {item.get('descricao') or item['codigo']}: "
                        f"há {saldo:g} em estoque, pedindo {quantidade:g}")
                valor_unit = linha.get("valor_unit")
                valor_unit = (float(valor_unit) if valor_unit not in (None, "")
                             else float(item.get("preco_venda") or 0))
                linhas.append((item, quantidade, valor_unit))

            venda_id = insert_returning_id(conn, """
                INSERT INTO vendas
                    (cliente_nome, cliente_telefone, cliente_cpf_cnpj,
                     forma_pagamento, garantia_texto, valor_total, criado_em, criado_por)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cliente_nome, cliente_telefone, cliente_cpf_cnpj, forma_pagamento,
                  garantia_texto, 0, _agora(), _autor()))

            total = 0.0
            for item, quantidade, valor_unit in linhas:
                dar_saida(conn, item["codigo"], quantidade, origem="venda",
                         referencia=f"venda:{venda_id}")
                valor_total_item = round(valor_unit * quantidade, 2)
                total += valor_total_item
                execute(conn, """
                    INSERT INTO venda_itens
                        (venda_id, item_id, codigo, descricao, quantidade, valor_unit, valor_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (venda_id, item["id"], item["codigo"], item["descricao"],
                      quantidade, valor_unit, valor_total_item))

            execute(conn, "UPDATE vendas SET valor_total = ? WHERE id = ?",
                    (round(total, 2), venda_id))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    return jsonify({"mensagem": "Venda registrada", "id": venda_id}), 201


@vendas_bp.route("/vendas/<int:venda_id>", methods=["GET"])
def detalhe(venda_id):
    with db_conn() as conn:
        venda = fetch_one(conn, "SELECT * FROM vendas WHERE id = ?", (venda_id,))
        if not venda:
            return jsonify({"erro": "Venda não encontrada"}), 404
        itens = fetch_all(conn, "SELECT * FROM venda_itens WHERE venda_id = ? ORDER BY id", (venda_id,))
    return jsonify({"venda": venda, "itens": itens})
