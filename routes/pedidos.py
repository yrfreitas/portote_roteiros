"""Vincular compras de peça (planilha) a clientes, direto pelo site.

A planilha de Pedidos é alimentada automaticamente pelo robô do
porto_tec_panasonic com as compras na CrediPay — mas ela só sabe nota fiscal
e valor. Quem é o cliente final e qual peça é aquilo só a equipe sabe, e até
agora isso teria que ser digitado na mão na planilha.

Aqui a equipe escolhe o cliente de uma lista (os que já existem nas fichas do
site), o que garante que o nome gravado é idêntico ao do site — e aí a
conciliação ao finalizar a rota casa exato em vez de aproximado.
"""
import logging

from flask import Blueprint, jsonify, request

from database import db_conn, fetch_all

log = logging.getLogger("portotec.pedidos")

pedidos_bp = Blueprint("pedidos", __name__)


@pedidos_bp.route("/pedidos/diagnostico", methods=["GET"])
def diagnostico_planilha():
    """Diz o que falta pra integração funcionar, sem expor nenhum segredo."""
    from services.planilha import diagnostico
    return jsonify(diagnostico())


@pedidos_bp.route("/pedidos", methods=["GET"])
def listar():
    """Compras de peça. ?todos=true traz também as já vinculadas."""
    from services.planilha import (faltando_para_configurar, listar_pedidos,
                                   planilha_configurada)

    if not planilha_configurada():
        falta = faltando_para_configurar()
        return jsonify({
            "erro": "Integração com a planilha não está configurada. "
                    "Falta: " + "; ".join(falta),
            "faltando": falta,
            "configurada": False,
        }), 503

    todos = str(request.args.get("todos", "")).lower() in ("1", "true", "sim")

    try:
        pedidos = listar_pedidos(apenas_pendentes=not todos)
    except Exception as exc:
        log.exception("Falha ao listar pedidos da planilha")
        return jsonify({"erro": f"Falha ao ler a planilha: {exc}"}), 502

    # Clientes já cadastrados no site, pra oferecer como lista de escolha —
    # escolher em vez de digitar é o que faz a conciliação casar exato depois.
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT DISTINCT s.cliente, s.tipo_aparelho, s.modelo
              FROM servicos s
             WHERE s.cliente IS NOT NULL AND TRIM(s.cliente) <> ''
             ORDER BY s.cliente
        """)

    clientes = [
        {"nome": l["cliente"],
         "aparelho": l.get("tipo_aparelho") or "",
         "modelo": l.get("modelo") or ""}
        for l in linhas
    ]

    return jsonify({"configurada": True, "pedidos": pedidos, "clientes": clientes})


@pedidos_bp.route("/pedidos/<int:linha>", methods=["PUT"])
def vincular(linha):
    from services.planilha import atualizar_pedido, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503

    data = request.get_json(silent=True) or {}
    cliente = (data.get("cliente") or "").strip()
    peca = (data.get("peca") or "").strip()
    numero_os = (data.get("numero_os") or "").strip()

    if not cliente:
        return jsonify({"erro": "Informe o cliente"}), 400
    if linha < 2:
        return jsonify({"erro": "Linha inválida (a 1 é o cabeçalho)"}), 400

    try:
        atualizar_pedido(linha, cliente, peca, numero_os)
    except Exception as exc:
        log.exception("Falha ao vincular pedido na linha %s", linha)
        return jsonify({"erro": f"Falha ao gravar na planilha: {exc}"}), 502

    return jsonify({"mensagem": f"Peça vinculada a {cliente}", "linha": linha})
