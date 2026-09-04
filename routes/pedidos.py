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
import re
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database import (bump_revisao, db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id, sql)

log = logging.getLogger("portotec.pedidos")

pedidos_bp = Blueprint("pedidos", __name__)


def _resumo_os(o: dict) -> dict:
    """Só o que a tela precisa mostrar de uma OS. O objeto cru do AgoraOS traz
    ~45 campos, a maioria interna dele — mandar tudo pro browser é peso à toa."""
    if not o:
        return None
    aparelhos = [
        (e.get("modelo") or e.get("descricao") or "").strip()
        for e in (o.get("equipamentos") or [])
    ]
    return {
        "id": o.get("id"),
        "data": (o.get("data") or "")[:10],
        "status": o.get("status"),
        "cliente": (o.get("cliente") or {}).get("nome"),
        "aparelhos": [a for a in aparelhos if a],
    }


def _resumo_previa(p: dict) -> dict:
    return {
        "pode_aplicar": p["pode_aplicar"],
        "pendencias": p["pendencias"],
        "forca": p["forca"],
        "os": _resumo_os(p["os"]),
        "os_candidatas": [_resumo_os(o) for o in p["os_candidatas"]],
        "produto": p["produto"],
        "produto_candidatos": p["produto_candidatos"],
        "qtd": p["qtd"],
        "controla_estoque": p["controla_estoque"],
    }


def _ja_lancada(linha: int):
    """A peça dessa linha já foi pro AgoraOS? Consulta a trava de idempotência."""
    with db_conn() as conn:
        return fetch_one(conn, sql(
            "SELECT id_os, id_item, peca, criado_em FROM pecas_agoraos "
            "WHERE linha_planilha = ?"), (linha,))


def _registrar(linha, cliente, peca, previa, lancado):
    with db_conn(commit=True) as conn:
        execute(conn, sql("""
            INSERT INTO pecas_agoraos
                (linha_planilha, id_os, id_produto_extensao, id_item,
                 cliente, peca, qtd, forca)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (linha, int(previa["os"]["id"]),
               int(previa["produto"]["id_produto_extensao"]),
               str(lancado.get("id_item") or ""), cliente, peca,
               float(lancado.get("qtd") or 1), previa["forca"]))


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


@pedidos_bp.route("/pedidos/emitidos-email", methods=["GET"])
def pedidos_emitidos_email():
    """Pedidos feitos na loja da Panasonic, lidos direto do e-mail de
    confirmação -- aparece em Peças Compradas sem esperar o robô da
    planilha achar a nota fiscal (achado em 2026-09-03: o robô estava
    parado pra pedidos recentes, dias sem gravar nada na planilha).

    A leitura do e-mail é só isso -- LEITURA, recalculada a cada chamada.
    O que o usuário PREENCHE aqui (peça/cliente/se já foi mandado pra
    agendar) mora em `pedidos_email` (ver database.py), casada pela
    `chave` estável que services/nfe.py calcula a partir de código+data.
    Pedido de 2026-09-03: "tem que ficar igual fica os faturados, pq eu
    tenho que anexar pra poder agendar os clientes com essas peças."
    """
    from services.nfe import pedidos_emitidos_recentes

    pedidos = pedidos_emitidos_recentes()
    if pedidos:
        with db_conn(commit=True) as conn:
            marcadores = ",".join(["?"] * len(pedidos))
            chaves = tuple(p["chave"] for p in pedidos)
            vinculos = {
                l["chave"]: l
                for l in fetch_all(conn, sql(
                    f"SELECT chave, peca, cliente_final FROM pedidos_email WHERE chave IN ({marcadores})"),
                    chaves)
            }
            agendados = {
                l["chave"]: l["ordem_servico_id"]
                for l in fetch_all(conn, sql(
                    f"SELECT chave, ordem_servico_id FROM pecas_chegada "
                    f"WHERE chave IN ({marcadores}) AND ordem_servico_id IS NOT NULL"),
                    chaves)
            }
            # Autocorreção (2026-09-04): antes da correção desta rota, agendar
            # gravava o id da OS só em pedidos_email -- essa OS nunca aparecia
            # no lado certo da fila de Agendar Clientes (ver EXISTS em
            # pecas_chegada, routes/ordens_servico.py:listar). Sem coluna nova
            # pra marcar "já migrado": se achar um caso desses agora, escreve
            # em pecas_chegada na hora, pra próxima vez já vir corrigido.
            for l in fetch_all(conn, sql(
                f"SELECT chave, ordem_servico_id FROM pedidos_email "
                f"WHERE chave IN ({marcadores}) AND ordem_servico_id IS NOT NULL"),
                chaves):
                if l["chave"] in agendados:
                    continue
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                existe = fetch_one(conn, sql("SELECT chave FROM pecas_chegada WHERE chave = ?"), (l["chave"],))
                if existe:
                    execute(conn, sql("UPDATE pecas_chegada SET ordem_servico_id = ? WHERE chave = ?"),
                            (l["ordem_servico_id"], l["chave"]))
                else:
                    execute(conn, sql(
                        "INSERT INTO pecas_chegada (chave, chegou_em, ordem_servico_id) VALUES (?, ?, ?)"),
                        (l["chave"], agora, l["ordem_servico_id"]))
                agendados[l["chave"]] = l["ordem_servico_id"]
        for p in pedidos:
            v = vinculos.get(p["chave"]) or {}
            p["peca"] = v.get("peca") or ""
            p["cliente_final"] = v.get("cliente_final") or ""
            p["ordem_servico_id"] = agendados.get(p["chave"])

    return jsonify({"pedidos": pedidos})


@pedidos_bp.route("/pedidos/email/<chave>", methods=["PUT"])
def vincular_pedido_email(chave):
    """Salva peça/cliente de um pedido emitido lido do e-mail (ver rota
    acima) -- equivalente ao PUT /pedidos/<linha> da planilha, mas numa
    tabela própria porque não existe linha de planilha pra esses ainda."""
    data = request.get_json(silent=True) or {}
    cliente = (data.get("cliente") or "").strip()
    peca = (data.get("peca") or "").strip()
    codigo = (data.get("codigo") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    data_email = (data.get("data_email") or "").strip()

    if not cliente:
        return jsonify({"erro": "Informe o cliente"}), 400

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_conn(commit=True) as conn:
        existe = fetch_one(conn, sql("SELECT chave FROM pedidos_email WHERE chave = ?"), (chave,))
        if existe:
            execute(conn, sql(
                "UPDATE pedidos_email SET peca = ?, cliente_final = ?, atualizado_em = ? "
                "WHERE chave = ?"), (peca, cliente, agora, chave))
        else:
            execute(conn, sql(
                "INSERT INTO pedidos_email "
                "(chave, codigo, descricao, data_email, peca, cliente_final, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)"),
                (chave, codigo, descricao, data_email, peca, cliente, agora))
        bump_revisao(conn)

    return jsonify({"mensagem": f"Peça vinculada a {cliente}", "chave": chave})


@pedidos_bp.route("/pedidos/email/<chave>", methods=["DELETE"])
def desvincular_pedido_email(chave):
    """Desfaz o vínculo peça/cliente de um pedido emitido (ver PUT acima) --
    pra quem digitou errado e o pedido ainda não foi mandado pra agendar.
    Não mexe em ordem_servico_id: uma OS já criada não se desfaz sozinha
    apagando a linha, tem que cancelar a OS de verdade primeiro.
    """
    with db_conn(commit=True) as conn:
        registro = fetch_one(conn, sql(
            "SELECT ordem_servico_id FROM pecas_chegada WHERE chave = ?"), (chave,))
        if registro and registro.get("ordem_servico_id"):
            return jsonify({"erro": "Já foi mandado pra Agendar Clientes -- "
                                     "cancele a OS antes de desvincular."}), 409
        execute(conn, sql("DELETE FROM pedidos_email WHERE chave = ?"), (chave,))
        bump_revisao(conn)
    return jsonify({"mensagem": "Vínculo desfeito"})


@pedidos_bp.route("/pedidos/email/agendar-cliente", methods=["POST"])
def agendar_cliente_email():
    """Mesma ideia de POST /pedidos/<linha>/agendar-cliente (planilha) --
    E O MESMO MECANISMO, de propósito: a fila de Agendar Clientes separa
    o lado "peça chegou" checando `EXISTS (... FROM pecas_chegada WHERE
    ordem_servico_id = os.id)` (ver GET /ordens-servico). Corrigido em
    2026-09-04: a primeira versão gravava em `pedidos_email.ordem_servico_id`
    (tabela só nossa) em vez de `pecas_chegada`, então a OS nascia sem
    bater nesse EXISTS e caía no lado errado da fila (José Airton, OS 125).
    `pedidos_email` continua guardando só peça/cliente (texto digitado);
    `pecas_chegada` é quem manda a partir de agora pra "já foi agendado".
    """
    from routes.clientes import criar_cliente

    data = request.get_json(silent=True) or {}
    chave = (data.get("chave") or "").strip()
    cliente_nome = (data.get("cliente") or "").strip()
    peca = (data.get("peca") or "").strip()
    if not chave or not cliente_nome:
        return jsonify({"erro": "Falta a chave do pedido ou o nome do cliente"}), 400

    with db_conn(commit=True) as conn:
        registro = fetch_one(conn, sql(
            "SELECT chave, ordem_servico_id FROM pecas_chegada WHERE chave = ?"), (chave,))
        if registro and registro.get("ordem_servico_id"):
            return jsonify({
                "erro": "Essa peça já está na fila de Agendar Clientes",
                "id": registro["ordem_servico_id"],
            }), 409

        existente = fetch_one(conn, sql(
            "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)"), (cliente_nome,))
        if existente:
            cliente_id = existente["id"]
        else:
            try:
                cliente_id = criar_cliente(conn, {"nome": cliente_nome})
            except ValueError as exc:
                return jsonify({"erro": str(exc)}), 400

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quem = (session.get("usuario_nome") or "Administrador").strip()[:80]
        os_id = insert_returning_id(conn, sql("""
            INSERT INTO ordens_servico
                (cliente_id, atendente, defeito_declarado, taxa_avaliacao,
                 status, observacao, criado_em, criado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (cliente_id, quem,
               f"Peça pedida: {peca}" if peca else "Peça pedida — agendar visita",
               0, "aguardando_agendamento",
               "Vindo de Peças Compradas (pedido emitido, direto do e-mail).", agora, quem))

        if registro:
            execute(conn, sql(
                "UPDATE pecas_chegada SET ordem_servico_id = ? WHERE chave = ?"),
                (os_id, chave))
        else:
            execute(conn, sql(
                "INSERT INTO pecas_chegada (chave, chegou_em, ordem_servico_id) "
                "VALUES (?, ?, ?)"), (chave, agora, os_id))

        # Salva peça/cliente em pedidos_email também (texto exibido na tela),
        # sem mais guardar ordem_servico_id lá -- pecas_chegada é quem manda.
        existe_email = fetch_one(conn, sql("SELECT chave FROM pedidos_email WHERE chave = ?"), (chave,))
        if existe_email:
            execute(conn, sql(
                "UPDATE pedidos_email SET peca = ?, cliente_final = ?, atualizado_em = ? WHERE chave = ?"),
                (peca, cliente_nome, agora, chave))
        else:
            execute(conn, sql(
                "INSERT INTO pedidos_email (chave, peca, cliente_final, atualizado_em) "
                "VALUES (?, ?, ?, ?)"), (chave, peca, cliente_nome, agora))
        bump_revisao(conn)

    return jsonify({"mensagem": f"{cliente_nome} enviado para Agendar Clientes",
                    "id": os_id, "cliente_id": cliente_id}), 201



# ─── Casamento entre a compra e quem pediu a peça ──────────────────────
#
# Fecha o circuito. O técnico registra "precisa da peça X para o cliente Y";
# dias depois a Panasonic avisa a compra por e-mail e o robô grava na aba
# Pedidos com a descrição da peça. Até aqui alguém tinha que lembrar de qual
# cliente era aquela compra e digitar o nome à mão.
#
# O casamento é pelo CÓDIGO da peça, não pela descrição: código é exato
# ("ARBPC1A12880"), descrição varia entre o que o técnico digita e o que vem
# na nota fiscal.
#
# SUGERE, NÃO GRAVA SOZINHO. Duas pessoas podem precisar da mesma peça na
# mesma semana, e este projeto já documenta (services/agoraos.py) que
# casamento automático de cliente produziu erro real em produção — escreveu
# na OS de outra pessoa e a API não tinha como desfazer. Quando há uma
# solicitação só, é um clique para aplicar; quando há mais de uma, a tela
# mostra as opções em vez de escolher no lugar de quem sabe.
RE_CODIGO_PECA = re.compile(r"([A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)?)")


def _codigos_da_peca(texto: str) -> set:
    """Códigos de peça encontrados num texto. Exige dígito: sem isso
    palavras da descrição ("PLACA", "CONJ") virariam código."""
    return {c for c in RE_CODIGO_PECA.findall((texto or "").upper())
            if any(ch.isdigit() for ch in c)}


def _solicitacoes_abertas(conn):
    """Peças que o técnico pediu e que ainda não foram ligadas a uma compra."""
    return fetch_all(conn, sql("""
        SELECT d.servico_id, d.peca, d.pedido_em, s.cliente,
               s.tipo_aparelho, s.modelo, s.numero_os
          FROM servico_desfecho d
          JOIN servicos s ON s.id = d.servico_id
         WHERE d.desfecho = 'precisa_peca'
           AND s.cliente IS NOT NULL AND TRIM(s.cliente) <> ''
    """))


def _sugerir_cliente(pedidos, solicitacoes):
    """Anota em cada compra qual cliente pediu aquela peça."""
    indice = []
    for s in solicitacoes:
        for codigo in _codigos_da_peca(s.get("peca")):
            indice.append((codigo, s))

    for p in pedidos:
        if p.get("cliente_final"):
            continue
        codigos = _codigos_da_peca(p.get("peca"))
        if not codigos:
            continue

        achados, vistos = [], set()
        for codigo, s in indice:
            if codigo in codigos and s["servico_id"] not in vistos:
                vistos.add(s["servico_id"])
                achados.append({
                    "servico_id": s["servico_id"],
                    "cliente": s["cliente"],
                    "peca": s["peca"],
                    "codigo": codigo,
                    "numero_os": s.get("numero_os") or "",
                    "aparelho": " ".join(x for x in [s.get("tipo_aparelho"),
                                                     s.get("modelo")] if x),
                    "ja_pedida": bool(s.get("pedido_em")),
                })
        if achados:
            p["sugestao_cliente"] = achados


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
        # incluir_criado=True: pedido de 2026-09-03 -- precisa vincular
        # cliente/agendar visita já no pedido EMITIDO (status CRIADO), sem
        # esperar o pagamento aprovar ou a nota faturar, senão a agenda
        # perde tempo esperando um dado que a loja já deu.
        pedidos = listar_pedidos(apenas_pendentes=not todos, incluir_criado=True)
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

    # Junta a chegada física. A planilha sabe até "Enviado"; quem recebe a
    # caixa é que sabe que chegou, e essa informação só existia na memória de
    # quem abriu o pacote.
    chaves = [(p.get("nota_fiscal") or ("PED" + (p.get("pedido") or ""))) for p in pedidos]
    chegadas = {}
    if chaves:
        with db_conn() as conn:
            marcadores = ",".join(["?"] * len(chaves))
            for l in fetch_all(
                conn,
                sql(f"SELECT chave, chegou_em, observacao, ordem_servico_id "
                    f"FROM pecas_chegada WHERE chave IN ({marcadores})"),
                tuple(chaves),
            ):
                chegadas[l["chave"]] = l
    for p, chave in zip(pedidos, chaves):
        registro = chegadas.get(chave)
        p["chave"] = chave
        p["chegou_em"] = (registro or {}).get("chegou_em") or ""
        p["chegou_obs"] = (registro or {}).get("observacao") or ""
        # Já foi mandado pra fila de Agendar Clientes? guarda o id da OS pra
        # tela trocar o botão por "já enviado" em vez de deixar clicar de novo
        # e abrir uma segunda OS pra mesma peça.
        p["agendamento_os_id"] = (registro or {}).get("ordem_servico_id")

    if not todos:
        # Pedido de 2026-08-29: só entra na lista padrão quem está A CAMINHO
        # (status_compra ENVIADO) OU já foi marcado "chegou" no site — nessa
        # ordem, DEPOIS da chegada estar juntada acima. APROVADO/FATURADO
        # (comprado mas ainda sem despacho) ficavam misturados com o que já
        # saiu de fato, confundindo quem vincula cliente. A condição do
        # chegou_em é o que a primeira tentativa (filtrar isso dentro de
        # listar_pedidos, sem saber de chegada) esqueceu: o status da
        # planilha pode avançar por conta própria além de ENVIADO sem
        # relação nenhuma com o site já ter recebido a peça — sem essa
        # condição, peça já em mãos sumia da tela.
        #
        # CRIADO entra também (2026-09-03): é o pedido recém EMITIDO — antes
        # ficava escondido até a nota faturar, e o Kalebe precisa vincular
        # cliente e agendar a visita assim que o pedido sai, não só quando
        # a caixa está a caminho.
        pedidos = [p for p in pedidos
                  if p["chegou_em"] or p["status_compra"].strip().upper() in ("ENVIADO", "CRIADO")]
        # Já foi mandado pra fila de Agendar Clientes? some da lista padrão
        # desta aba. O trabalho daqui (vincular a peça a um cliente) está
        # feito, e o que falta (marcar visita) já mora na outra tela — a
        # mesma peça aparecendo nas duas ao mesmo tempo é exatamente a
        # duplicação que confunde quem olha as duas abas. "mostrar todas"
        # continua trazendo de volta, pra quem quer conferir o histórico.
        pedidos = [p for p in pedidos if not p["agendamento_os_id"]]

    # Liga cada compra a quem pediu aquela peça em campo.
    with db_conn() as conn:
        _sugerir_cliente(pedidos, _solicitacoes_abertas(conn))

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

    # A planilha já está gravada — o AgoraOS é bônus e NUNCA pode derrubar o
    # vínculo. Por isso vem depois, dentro de try, e uma falha aqui só vira
    # aviso na resposta: o trabalho do usuário não se perde por causa do ERP.
    resposta = {"mensagem": f"Peça vinculada a {cliente}", "linha": linha}
    resposta["agoraos"] = _tentar_lancar(linha, cliente, peca, numero_os,
                                         (data.get("modelo") or "").strip(),
                                         data.get("qtd") or 1)
    return jsonify(resposta)


@pedidos_bp.route("/pedidos/<int:linha>/limpar", methods=["POST"])
def limpar_pedido(linha):
    """Esvazia peça/cliente de uma linha da planilha -- pedido de
    2026-09-04: "coloque um x pra eu poder remover". Rota separada do PUT
    normal (que exige cliente preenchido, pra um blur acidental de campo
    vazio nunca apagar um vínculo sem querer) -- só o clique explícito no X
    chega aqui. Não mexe em status_compra (é do robô) nem desfaz
    lançamento já feito no AgoraOS.
    """
    from services.planilha import atualizar_pedido, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503
    if linha < 2:
        return jsonify({"erro": "Linha inválida (a 1 é o cabeçalho)"}), 400

    try:
        atualizar_pedido(linha, "", "", "")
    except Exception as exc:
        log.exception("Falha ao limpar pedido na linha %s", linha)
        return jsonify({"erro": f"Falha ao gravar na planilha: {exc}"}), 502

    return jsonify({"mensagem": "Limpo", "linha": linha})


def _tentar_lancar(linha, cliente, peca, numero_os, modelo="", qtd=1):
    """Lança a peça no AgoraOS quando — e só quando — não há ambiguidade.

    Por que automático em vez de sempre perguntar: o Kalebe vincula peça em
    lote e uma confirmação por linha inviabiliza o uso. Por que não automático
    sempre: a API não apaga item de OS, então casamento duvidoso vira prévia
    em vez de estrago. É a mesma escada de confiança da conciliação da rota,
    que já provou funcionar.
    """
    from services import agoraos

    if not agoraos.configurado():
        return {"ativo": False}

    ja = _ja_lancada(linha)
    if ja:
        return {"ativo": True, "estado": "ja_lancada",
                "mensagem": f"Já estava lançada na OS {ja['id_os']} do AgoraOS",
                "id_os": ja["id_os"], "id_item": ja["id_item"]}

    try:
        previa = agoraos.preparar(cliente, peca, numero_os, modelo, qtd)
    except Exception as exc:
        log.exception("AgoraOS: falha ao preparar lançamento da linha %s", linha)
        return {"ativo": True, "estado": "erro", "mensagem": str(exc)}

    if not previa["pode_aplicar"]:
        return {"ativo": True, "estado": "revisar",
                "mensagem": "; ".join(previa["pendencias"]),
                "previa": _resumo_previa(previa)}

    try:
        lancado = agoraos.lancar_item(previa["os"]["id"],
                                      previa["produto"]["id_produto_extensao"], qtd)
        _registrar(linha, cliente, peca, previa, lancado)
    except Exception as exc:
        log.exception("AgoraOS: falha ao lançar peça da linha %s", linha)
        return {"ativo": True, "estado": "erro", "mensagem": str(exc)}

    aviso = None
    if not previa["controla_estoque"]:
        # Dito na cara: o item entrou na OS, mas não reduziu saldo — porque
        # nenhum produto do AgoraOS está com controle de estoque ligado.
        aviso = ("Lançado na OS, mas o produto está sem controle de estoque "
                 "no AgoraOS — não reduziu saldo.")

    return {"ativo": True, "estado": "lancada", "forca": previa["forca"],
            "id_os": previa["os"]["id"], "id_item": lancado.get("id_item"),
            "produto": previa["produto"]["nome"], "aviso": aviso or lancado.get("aviso"),
            "mensagem": f"Lançada na OS {previa['os']['id']} do AgoraOS"}


@pedidos_bp.route("/pedidos/<int:linha>/agoraos/previa", methods=["POST"])
def previa_agoraos(linha):
    """Mostra o que seria lançado, sem gravar nada. É a tela de decisão."""
    from services import agoraos

    if not agoraos.configurado():
        return jsonify({"configurada": False,
                        "faltando": agoraos.faltando_para_configurar()}), 503

    data = request.get_json(silent=True) or {}
    ja = _ja_lancada(linha)
    if ja:
        return jsonify({"configurada": True, "ja_lancada": True,
                        "id_os": ja["id_os"], "id_item": ja["id_item"],
                        "criado_em": ja["criado_em"]})

    try:
        previa = agoraos.preparar(
            (data.get("cliente") or "").strip(),
            (data.get("peca") or "").strip(),
            (data.get("numero_os") or "").strip(),
            (data.get("modelo") or "").strip(),
            data.get("qtd") or 1,
        )
    except Exception as exc:
        log.exception("AgoraOS: prévia falhou na linha %s", linha)
        return jsonify({"erro": str(exc)}), 502

    return jsonify({"configurada": True, "ja_lancada": False,
                    **_resumo_previa(previa)})


@pedidos_bp.route("/pedidos/<int:linha>/agoraos", methods=["POST"])
def lancar_agoraos(linha):
    """Lança de verdade, com OS e produto ESCOLHIDOS na tela.

    Rota separada da prévia de propósito: aqui o id da OS e o do produto vêm
    explícitos do cliente, não de adivinhação. É o caminho de quem revisou uma
    ambiguidade e decidiu — o único jeito de lançar num caso duvidoso.
    """
    from services import agoraos

    if not agoraos.configurado():
        return jsonify({"erro": "AgoraOS não configurado. Falta: " +
                        ", ".join(agoraos.faltando_para_configurar())}), 503

    data = request.get_json(silent=True) or {}
    id_os = data.get("id_os")
    id_prod = data.get("id_produto_extensao")
    if not id_os or not id_prod:
        return jsonify({"erro": "Informe id_os e id_produto_extensao"}), 400

    if _ja_lancada(linha):
        return jsonify({"erro": "Essa linha já foi lançada no AgoraOS. "
                                "A API não apaga item de OS — remova por lá "
                                "antes de lançar de novo."}), 409

    qtd = float(data.get("qtd") or 1)
    try:
        lancado = agoraos.lancar_item(id_os, id_prod, qtd)
    except Exception as exc:
        log.exception("AgoraOS: falha ao lançar linha %s escolhida na mão", linha)
        return jsonify({"erro": str(exc)}), 502

    # Registro montado à mão porque aqui a escolha foi humana: a "força" do
    # casamento é justamente ter sido uma pessoa que decidiu.
    _registrar(linha, (data.get("cliente") or "").strip(),
               (data.get("peca") or "").strip(),
               {"os": {"id": id_os},
                "produto": {"id_produto_extensao": id_prod},
                "forca": "escolha manual"},
               lancado)

    return jsonify({"mensagem": f"Peça lançada na OS {id_os} do AgoraOS",
                    "id_os": id_os, "id_item": lancado.get("id_item"),
                    "aviso": lancado.get("aviso")})


@pedidos_bp.route("/pedidos/agoraos/diagnostico", methods=["GET"])
def diagnostico_agoraos():
    """Estado da integração com o AgoraOS, sem expor senha."""
    from services import agoraos
    return jsonify(agoraos.diagnostico())


@pedidos_bp.route("/pedidos/chegada", methods=["POST"])
def marcar_chegada():
    """Registra que a peça chegou fisicamente na oficina — ou desfaz.

    Existe porque o último estado que a Panasonic informa é "Enviado", e entre
    o envio e a peça na mão passam dias. Quem vai reagendar a visita do técnico
    não pergunta "foi enviada?", pergunta "chegou?". Sem isso, a resposta
    dependia de alguém lembrar de ter aberto a caixa.
    """
    data = request.get_json(silent=True) or {}
    chave = (data.get("chave") or "").strip()
    if not chave:
        return jsonify({"erro": "chave é obrigatória"}), 400

    chegou = bool(data.get("chegou", True))
    observacao = (data.get("observacao") or "").strip()[:300]
    quem = (session.get("usuario_nome") or "").strip()[:80]

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_conn(commit=True) as conn:
        if not chegou:
            # Desmarcar APAGA a linha em vez de gravar chegou_em vazio: marcar
            # por engano e desfazer tem que voltar ao estado anterior de fato,
            # não deixar um registro fantasma que confunde a leitura depois.
            execute(conn, sql("DELETE FROM pecas_chegada WHERE chave = ?"), (chave,))
            bump_revisao(conn)
            return jsonify({"chave": chave, "chegou_em": ""})

        ja = fetch_one(conn, sql("SELECT chave FROM pecas_chegada WHERE chave = ?"),
                       (chave,))
        if ja:
            execute(conn, sql(
                "UPDATE pecas_chegada SET chegou_em = ?, observacao = ?, "
                "registrado_por = ? WHERE chave = ?"),
                (agora, observacao, quem, chave))
        else:
            execute(conn, sql(
                "INSERT INTO pecas_chegada (chave, chegou_em, observacao, "
                "registrado_por) VALUES (?, ?, ?, ?)"),
                (chave, agora, observacao, quem))
        bump_revisao(conn)

    return jsonify({"chave": chave, "chegou_em": agora, "registrado_por": quem})


@pedidos_bp.route("/pedidos/clientes", methods=["POST"])
def cadastrar_cliente_rapido():
    """Cadastra um cliente direto da aba Peças — pelo mesmo formulário mínimo
    do "+" ao lado do campo Cliente da linha.

    Rota própria em vez de reaproveitar POST /api/clientes na cara: aquela
    exige a permissão `ordens_servico`, e quem só mexe em Peças (permissão
    `pecas`) ficaria travado num botão da própria tela dele. Aqui dentro de
    /api/pedidos herda `pecas`, que é a permissão certa pra essa ação.
    """
    from routes.clientes import criar_cliente

    dados = request.get_json(silent=True) or {}
    try:
        with db_conn(commit=True) as conn:
            novo_id = criar_cliente(conn, dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Cliente cadastrado", "id": novo_id}), 201


@pedidos_bp.route("/pedidos/<int:linha>/agendar-cliente", methods=["POST"])
def agendar_cliente(linha):
    """Manda o cliente dessa compra pra fila de "Agendar Clientes": acha (ou
    cadastra) o cliente no cadastro do site e abre uma Ordem de Serviço em
    'aguardando_agendamento' — a mesma fila que toda OS nova cai antes de ter
    uma visita marcada.

    Fecha um buraco real: a peça chega, tem dono (o campo Cliente já
    preenchido aqui), e até agora não havia pra onde levar isso sem redigitar
    cliente/aparelho na mão em Roteiros. Uma OS por peça — a trava é
    `pecas_chegada.ordem_servico_id`: clicar duas vezes na mesma linha não
    abre duas OS, só aponta pra que já existe.
    """
    from routes.clientes import criar_cliente

    data = request.get_json(silent=True) or {}
    chave = (data.get("chave") or "").strip()
    cliente_nome = (data.get("cliente") or "").strip()
    peca = (data.get("peca") or "").strip()
    if not chave or not cliente_nome:
        return jsonify({"erro": "Falta a chave da compra ou o nome do cliente"}), 400

    with db_conn(commit=True) as conn:
        registro = fetch_one(conn, sql(
            "SELECT chave, ordem_servico_id FROM pecas_chegada WHERE chave = ?"),
            (chave,))
        if registro and registro.get("ordem_servico_id"):
            return jsonify({
                "erro": "Essa peça já está na fila de Agendar Clientes",
                "id": registro["ordem_servico_id"],
            }), 409

        existente = fetch_one(conn, sql(
            "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)"), (cliente_nome,))
        if existente:
            cliente_id = existente["id"]
        else:
            try:
                cliente_id = criar_cliente(conn, {"nome": cliente_nome})
            except ValueError as exc:
                return jsonify({"erro": str(exc)}), 400

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quem = (session.get("usuario_nome") or "Administrador").strip()[:80]
        os_id = insert_returning_id(conn, sql("""
            INSERT INTO ordens_servico
                (cliente_id, atendente, defeito_declarado, taxa_avaliacao,
                 status, observacao, criado_em, criado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (cliente_id, quem,
               f"Peça chegou: {peca}" if peca else "Peça chegou — agendar revisita",
               0, "aguardando_agendamento",
               f"Vindo da aba Peças (linha {linha} da planilha).", agora, quem))

        if registro:
            execute(conn, sql(
                "UPDATE pecas_chegada SET ordem_servico_id = ? WHERE chave = ?"),
                (os_id, chave))
        else:
            # A peça foi mandada pra agendar sem passar por "marcar chegada"
            # antes (a tela permite, já que o cliente já está preenchido) —
            # cria o registro na hora, já com a chegada implícita em agora.
            execute(conn, sql(
                "INSERT INTO pecas_chegada (chave, chegou_em, ordem_servico_id) "
                "VALUES (?, ?, ?)"), (chave, agora, os_id))
        bump_revisao(conn)

    return jsonify({"mensagem": f"{cliente_nome} enviado para Agendar Clientes",
                    "id": os_id, "cliente_id": cliente_id}), 201
