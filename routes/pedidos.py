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
    """Diz o que falta pra integração funcionar, sem expor nenhum segredo.

    ?testar=true também abre a conexão com o e-mail pra confirmar que a
    senha de app é aceita — só dizer que a variável existe não prova nada.
    """
    from services.nfe import diagnostico_imap
    from services.planilha import diagnostico

    testar = str(request.args.get("testar", "")).lower() in ("1", "true", "sim")

    return jsonify({
        "planilha": diagnostico(),
        "email": diagnostico_imap(testar_conexao=testar),
    })


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

    # A sugestão de peça NÃO é feita aqui de propósito: ler os XMLs das notas
    # por IMAP levava 24s e a tela ficava travada em "carregando" (e o Railway
    # cortaria a requisição). Vem por /pedidos/sugestoes, chamado depois que a
    # lista já apareceu.
    for p in pedidos:
        p["peca_sugerida"] = ""
        p["itens_nota"] = []

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

    from services.nfe import imap_configurado as _imap_ok

    return jsonify({
        "configurada": True,
        "pedidos": pedidos,
        "clientes": clientes,
        "sugestao_peca_ativa": _imap_ok(),
        "pendentes": sum(1 for p in pedidos if not p["cliente_final"]),
    })


@pedidos_bp.route("/pedidos/sugestoes", methods=["GET"])
def sugerir_pecas():
    """Peças lidas do XML da NF-e, por chave de nota.

    Separado da listagem porque ler os XMLs por IMAP é lento (~24s pra 18
    notas): a tela mostra a lista na hora e preenche as sugestões quando
    chegarem, em vez de ficar travada carregando.
    """
    from services.nfe import imap_configurado, pecas_por_nota

    if not imap_configurado():
        return jsonify({"ativo": False, "sugestoes": {}})

    chaves = [c.strip() for c in (request.args.get("notas") or "").split(",") if c.strip()]
    if not chaves:
        return jsonify({"ativo": True, "sugestoes": {}})

    # Trava de segurança: uma requisição não pode varrer a caixa inteira.
    chaves = chaves[:40]

    try:
        achadas = pecas_por_nota(chaves)
    except Exception:
        log.exception("Falha ao buscar peças nas notas fiscais")
        return jsonify({"ativo": True, "sugestoes": {}, "erro": True})

    return jsonify({
        "ativo": True,
        "sugestoes": {k: v["resumo"] for k, v in achadas.items()},
    })


@pedidos_bp.route("/pedidos/revisar", methods=["GET"])
def revisar():
    """Baixas que casaram só pelo nome (as amarelas), pra conferência.

    Casar só por nome é o elo mais fraco — dois clientes homônimos, ou o
    mesmo nome em compras diferentes, dariam baixa na linha errada. Ficam
    marcadas de amarelo na planilha; aqui dá pra revisar sem caçar na mão.
    """
    from services.planilha import listar_conciliadas_fracas, planilha_configurada

    if not planilha_configurada():
        return jsonify({"itens": [], "configurada": False})

    try:
        return jsonify({"configurada": True, "itens": listar_conciliadas_fracas()})
    except Exception as exc:
        log.exception("Falha ao listar conciliações para revisão")
        return jsonify({"erro": f"Falha ao ler a planilha: {exc}"}), 502


@pedidos_bp.route("/pedidos/<int:linha>/desfazer", methods=["PUT"])
def desfazer(linha):
    """Tira a baixa de uma linha — quando a revisão mostra que casou errado."""
    from services.planilha import desfazer_baixa, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503
    if linha < 2:
        return jsonify({"erro": "Linha inválida"}), 400

    try:
        desfazer_baixa(linha)
    except Exception as exc:
        log.exception("Falha ao desfazer baixa na linha %s", linha)
        return jsonify({"erro": f"Falha ao gravar na planilha: {exc}"}), 502

    return jsonify({"mensagem": f"Baixa desfeita na linha {linha}"})


@pedidos_bp.route("/pedidos/pendentes", methods=["GET"])
def contar_pendentes():
    """Só a contagem, pro selo na aba. Não lê e-mail nem sugere peça —
    é chamado no carregamento da página e precisa ser barato."""
    from services.planilha import listar_pedidos, planilha_configurada

    if not planilha_configurada():
        return jsonify({"pendentes": 0, "configurada": False})

    try:
        return jsonify({
            "pendentes": len(listar_pedidos(apenas_pendentes=True)),
            "configurada": True,
        })
    except Exception:
        log.exception("Falha ao contar peças pendentes")
        return jsonify({"pendentes": 0, "configurada": True, "erro": True})


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


@pedidos_bp.route("/pedidos/lote", methods=["PUT"])
def vincular_lote():
    """Vincula várias linhas de uma vez. Cada item: {linha, cliente, peca}.

    Grava uma por uma e relata individualmente: se a 3ª falhar, as duas
    primeiras continuam valendo e o usuário vê exatamente qual não foi.
    """
    from services.planilha import atualizar_pedido, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503

    itens = (request.get_json(silent=True) or {}).get("itens") or []
    if not isinstance(itens, list) or not itens:
        return jsonify({"erro": "Nada para vincular"}), 400

    gravados, falhas = [], []
    for item in itens:
        try:
            linha = int(item.get("linha"))
        except (TypeError, ValueError):
            falhas.append({"linha": item.get("linha"), "erro": "linha inválida"})
            continue

        cliente = (item.get("cliente") or "").strip()
        if not cliente or linha < 2:
            falhas.append({"linha": linha, "erro": "cliente vazio ou linha inválida"})
            continue

        try:
            atualizar_pedido(linha, cliente, (item.get("peca") or "").strip(),
                             (item.get("numero_os") or "").strip())
            gravados.append(linha)
        except Exception as exc:
            log.exception("Falha ao vincular linha %s em lote", linha)
            falhas.append({"linha": linha, "erro": str(exc)})

    return jsonify({
        "gravados": gravados,
        "falhas": falhas,
        "mensagem": f"{len(gravados)} peça(s) vinculada(s)"
                    + (f", {len(falhas)} com erro" if falhas else ""),
    })
